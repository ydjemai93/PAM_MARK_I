import logging
import asyncio
import subprocess
import os
import json
import time
import signal
from typing import Dict, Any, Optional, List
import psutil
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self):
        self.agents_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agents")
        self.running_agents = {}  # Pour stocker les processus des agents en cours d'exécution
        self._ensure_agents_directory()
        self._load_running_agents()  # Charger les agents déjà en cours d'exécution
        logger.info(f"Service d'agents initialisé: répertoire={self.agents_directory}")
    
    def _ensure_agents_directory(self):
        """Crée le répertoire des agents s'il n'existe pas"""
        if not os.path.exists(self.agents_directory):
            os.makedirs(self.agents_directory)
            logger.info(f"Répertoire des agents créé: {self.agents_directory}")
    
    def _load_running_agents(self):
        """Charge l'état des agents en cours d'exécution"""
        try:
            state_file = os.path.join(self.agents_directory, "agent_state.json")
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    state = json.load(f)
                    
                # Vérifier quels processus sont réellement en cours d'exécution
                for agent_id, proc_info in state.items():
                    pid = proc_info.get("pid")
                    if pid and self._is_process_running(pid):
                        self.running_agents[agent_id] = proc_info
                        logger.info(f"Agent trouvé en cours d'exécution: id={agent_id}, pid={pid}")
                    else:
                        logger.info(f"Agent marqué comme en cours d'exécution mais introuvable: id={agent_id}")
                
                logger.info(f"État des agents chargé: {len(self.running_agents)} agents en cours d'exécution")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'état des agents: {e}")
    
    def _save_running_agents(self):
        """Sauvegarde l'état des agents en cours d'exécution"""
        try:
            state_file = os.path.join(self.agents_directory, "agent_state.json")
            with open(state_file, "w") as f:
                json.dump(self.running_agents, f)
            logger.debug("État des agents sauvegardé")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'état des agents: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Vérifie si un processus est en cours d'exécution"""
        try:
            # Vérifie si le processus existe
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    async def deploy_agent(self, agent_id: str, name: str, prompt_template: str) -> Dict[str, Any]:
        """Déploie un agent dans LiveKit"""
        start_time = time.time()
        logger.info(f"Déploiement de l'agent: id={agent_id}, name={name}")
        
        worker_id = f"agent-{agent_id}"
        
        # Vérifier si l'agent est déjà en cours d'exécution
        if worker_id in self.running_agents:
            logger.info(f"Agent déjà dé
