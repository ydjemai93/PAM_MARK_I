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
from dotenv import load_dotenv
from livekit.agents import cli, WorkerDefinition
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
    
    # Contexte initial pour l'LLM
    initial_ctx = lbm.ChatContext().append(
        role="system",
        content=ctx.job.metadata or ctx.proc.userdata.get("prompt_template") or DEFAULT_PROMPT
    )
    
    await ctx.connect(auto_subscribe=lbm.AutoSubscribe.AUDIO_ONLY)
    
    # Attendre le premier participant à rejoindre
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connecté: {participant.identity}")
    
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
    await agent.say("Bonjour, comment puis-je vous aider aujourd'hui?", allow_interruptions=True)
    
    # L'agent continuera à fonctionner automatiquement et traitera
    # la voix du participant jusqu'à ce que la salle soit fermée
    logger.info("Agent démarré et en attente d'interactions.")

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
    
    # Accepter la requête avec le nom d'agent configuré
    await req.accept(
        name=os.getenv("AGENT_NAME", "voice-assistant"),
        identity=os.getenv("AGENT_IDENTITY", "ai-assistant"),
    )

# Prompt par défaut pour l'agent
DEFAULT_PROMPT = """
Tu es un assistant téléphonique intelligent. Ta mission est d'aider l'utilisateur de manière efficace et professionnelle.
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
