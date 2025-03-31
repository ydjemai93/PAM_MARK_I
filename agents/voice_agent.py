#!/usr/bin/env python3
"""
Script pour démarrer un agent vocal LiveKit.
Ce script est destiné à être exécuté comme un processus séparé pour chaque agent.
"""

import os
import sys
import asyncio
import logging
import argparse
import json
from dotenv import load_dotenv
from livekit.agents import cli, WorkerDefinition, AutoSubscribe
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, deepgram, silero
from livekit.agents import lbm

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("voice_agent")

# Charger les variables d'environnement
load_dotenv()

async def entrypoint(ctx: lbm.JobContext):
    """
    Point d'entrée de l'agent vocal.
    Cette fonction est appelée lorsque l'agent rejoint une salle.
    """
    logger.info(f"Agent rejoignant la salle: {ctx.room.name}")
    
    # Récupérer les métadonnées du job (si disponibles)
    job_metadata = ctx.job.metadata
    metadata_dict = {}
    
    if job_metadata:
        try:
            metadata_dict = json.loads(job_metadata)
            logger.info(f"Métadonnées du job: {metadata_dict}")
        except json.JSONDecodeError:
            logger.warning(f"Impossible de décoder les métadonnées: {job_metadata}")
    
    # Récupérer le numéro de téléphone à appeler (pour les appels sortants)
    phone_number = metadata_dict.get("phone_number")
    call_id = metadata_dict.get("call_id")
    
    if phone_number:
        logger.info(f"Appel sortant vers: {phone_number}, call_id: {call_id}")
    
    # Contexte initial pour l'LLM
    initial_ctx = lbm.ChatContext().append(
        role="system",
        content=ctx.proc.userdata.get("prompt_template") or DEFAULT_PROMPT
    )
    
    # Se connecter à la salle
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
# Attendre le premier participant à rejoindre
    try:
        participant = await ctx.wait_for_participant(timeout=60)
        logger.info(f"Participant connecté: identity={participant.identity}, name={participant.name}")
    except asyncio.TimeoutError:
        logger.warning("Aucun participant n'a rejoint après 60 secondes, l'agent continuera son exécution")
        # Nous continuons même sans participant car dans le cas d'un appel sortant,
        # le participant SIP peut rejoindre plus tard
        participant = None
    
    # Si nous avons un numéro de téléphone, tenter de passer l'appel
    if phone_number and not participant:
        logger.info(f"Initiation de l'appel vers {phone_number}")
        try:
            # Récupérer le trunk_id des variables d'environnement
            trunk_id = os.getenv("TWILIO_SIP_TRUNK_ID")
            
            if not trunk_id:
                logger.error("Impossible d'initier l'appel: TWILIO_SIP_TRUNK_ID non défini")
            else:
                # Créer un participant SIP pour l'appel sortant
                participant_request = api.CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=phone_number,
                    room_name=ctx.room.name,
                    participant_identity=f"sip-{call_id or 'outbound'}",
                    participant_name="Outbound Call",
                    play_dialtone=True
                )
                
                sip_participant = await ctx.api.sip.create_sip_participant(participant_request)
                logger.info(f"Appel initié: {sip_participant}")
                
                # Attendre que le participant rejoigne
                participant = await ctx.wait_for_participant(identity=f"sip-{call_id or 'outbound'}", timeout=30)
                logger.info(f"Participant SIP connecté: {participant.identity}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initiation de l'appel: {e}")
    
    # Attendre encore si aucun participant n'est disponible
    if not participant:
        try:
            logger.info("En attente d'un participant...")
            participant = await ctx.wait_for_participant(timeout=120)
            logger.info(f"Participant connecté: {participant.identity}")
        except asyncio.TimeoutError:
            logger.error("Aucun participant n'a rejoint après 2 minutes, arrêt de l'agent")
            return
    
    # Initialiser l'agent vocal
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata.get("vad"),
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
        allow_interruptions=True,
    )
    
    # Démarrer l'agent pour le participant spécifique
    agent.start(ctx.room, participant)
    
    # Message de bienvenue
    welcome_message = "Bonjour, comment puis-je vous aider aujourd'hui?"
    if phone_number:
        welcome_message = "Bonjour, je suis votre assistant IA. Comment puis-je vous aider aujourd'hui?"
    
    await agent.say(welcome_message, allow_interruptions=True)
    
    # L'agent continuera à fonctionner automatiquement et traitera
    # la voix du participant jusqu'à ce que la salle soit fermée
    logger.info("Agent démarré et en attente d'interactions.")
    
    # Surveiller l'état de l'appel téléphonique
    if phone_number:
        # Boucle de surveillance de l'état de l'appel
        start_time = asyncio.get_event_loop().time()
        while True:
            # Vérifier si le participant est toujours connecté
            if not participant.is_connected:
                logger.info("Le participant a raccroché, fin de l'appel")
                break
                
            # Vérifier l'état de l'appel via les attributs du participant
            call_status = participant.attributes.get("sip.callStatus")
            if call_status == "hangup":
                logger.info("L'appel a été terminé")
                break
                
            # Timeout de sécurité (30 minutes maximum)
            if asyncio.get_event_loop().time() - start_time > 1800:  # 30 minutes
                logger.warning("Timeout de l'appel après 30 minutes")
                break
                
            await asyncio.sleep(5)  # Vérifier toutes les 5 secondes
    
    logger.info("Session agent terminée")

def prewarm_func(proc: lbm.JobProcess):
    """
    Fonction de préchauffage pour charger les modèles nécessaires.
    """
    logger.info("Préchauffage de l'agent vocal...")
    # Charger le modèle VAD de Silero
    proc.userdata["vad"] = silero.VAD.vad()
    # Stocker le template de prompt s'il est fourni
    prompt_template = os.getenv("AGENT_PROMPT_TEMPLATE")
    if prompt_template:
        proc.userdata["prompt_template"] = prompt_template
    logger.info("Préchauffage terminé.")

async def request_func(req: lbm.JobRequest):
    """
    Fonction appelée pour accepter ou rejeter une requête de job.
    """
    logger.info(f"Nouvelle requête reçue: room={req.room_name}, metadata={req.metadata}")
    
    # Récupérer les noms configurés
    agent_name = os.getenv("AGENT_NAME", "voice-assistant")
    agent_identity = os.getenv("AGENT_IDENTITY", "ai-assistant")
    
    # Accepter la requête avec le nom d'agent configuré
    await req.accept(
        name=agent_name,
        identity=agent_identity,
    )

# Prompt par défaut pour l'agent
DEFAULT_PROMPT = """
Tu es un assistant téléphonique IA sophistiqué. Ta mission est d'aider l'utilisateur de manière efficace et professionnelle.
Ton rôle est de comprendre rapidement les besoins de l'appelant et de fournir des réponses claires et concises.
Sois poli, patient et empathique dans toutes tes interactions.
N'oublie pas que l'utilisateur ne peut pas te voir, donc sois explicite dans tes explications.
Si tu ne connais pas une réponse, admets-le honnêtement et propose d'autres moyens pour aider l'utilisateur.
"""

def main():
    parser = argparse.ArgumentParser(description="Démarrer un agent vocal LiveKit")
    parser.add_argument("--agent-id", type=str, help="ID unique de l'agent")
    parser.add_argument("--agent-name", type=str, help="Nom de l'agent")
    parser.add_argument("--prompt-template", type=str, help="Template de prompt pour l'agent")
    
    args = parser.parse_args()
    
    # Configuration des variables d'environnement en fonction des arguments
    if args.agent_id:
        os.environ["AGENT_IDENTITY"] = f"agent-{args.agent_id}"
    
    if args.agent_name:
        os.environ["AGENT_NAME"] = args.agent_name
    
    if args.prompt_template:
        os.environ["AGENT_PROMPT_TEMPLATE"] = args.prompt_template
    
    # Configuration de l'agent
    worker = WorkerDefinition(
        entrypoint_run=entrypoint,
        request_run=request_func,
        prewarm_run=prewarm_func,
        agent_name=os.getenv("AGENT_NAME", "voice-assistant"),
    )
    
    logger.info(f"Démarrage de l'agent: {os.getenv('AGENT_NAME', 'voice-assistant')}")
    
    # Démarrer l'agent
    cli.run_app(worker)

if __name__ == "__main__":
    main()
