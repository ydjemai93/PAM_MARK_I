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
