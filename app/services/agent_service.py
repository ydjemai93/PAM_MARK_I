import logging
import time
import subprocess
import os
import sys
import asyncio
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class AgentService:
    """
    Service pour gérer les agents vocaux
    """
    
    def __init__(self):
        self.running_agents = {}
        self.agent_processes = {}
        logger.info("Service d'agents initialisé")
    
    async def deploy_agent(self, agent_id: str, name: str, prompt_template: str) -> Dict[str, Any]:
        """
        Déploie un agent vocal dans un processus séparé
        """
        worker_id = f"agent-{agent_id}"
        
        # Vérifier si l'agent est déjà en cours d'exécution
        if worker_id in self.running_agents and self.running_agents[worker_id].get("status") == "running":
            logger.info(f"L'agent {worker_id} est déjà en cours d'exécution")
            return {
                "agent_id": agent_id,
                "worker_id": worker_id,
                "status": "already_running"
            }
        
        logger.info(f"Déploiement de l'agent: id={agent_id}, name={name}")
        
        # Chemin vers le script d'agent
        agent_script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "agents", "voice_agent.py"
        )
        
        # Vérifier que le script existe
        if not os.path.exists(agent_script_path):
            logger.error(f"Script d'agent introuvable: {agent_script_path}")
            return {
                "status": "error",
                "error": f"Agent script not found: {agent_script_path}"
            }
        
        # Configuration de l'agent
        env = os.environ.copy()
        env["AGENT_NAME"] = worker_id
        env["AGENT_IDENTITY"] = f"agent-id-{agent_id}"
        
        if prompt_template:
            env["AGENT_PROMPT_TEMPLATE"] = prompt_template
        
        try:
            # Démarrer le processus d'agent
            cmd = [sys.executable, agent_script_path, "--agent-id", agent_id, "--agent-name", worker_id]
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Enregistrer le processus
            self.agent_processes[worker_id] = process
            
            # Attendre un peu pour que l'agent démarre
            await asyncio.sleep(2)
            
            # Vérifier si le processus est toujours en cours d'exécution
            if process.poll() is not None:
                stderr = process.stderr.read()
                logger.error(f"L'agent {worker_id} s'est arrêté prématurément: {stderr}")
                return {
                    "status": "error",
                    "error": f"Agent process failed to start: {stderr}"
                }
            
            # Enregistrer l'agent comme en cours d'exécution
            self.running_agents[worker_id] = {
                "agent_id": agent_id,
                "name": name,
                "status": "running",
                "deployed_at": time.time()
            }
            
            logger.info(f"Agent déployé avec succès: id={agent_id}, worker_id={worker_id}")
            
            return {
                "agent_id": agent_id,
                "worker_id": worker_id,
                "status": "deployed"
            }
        except Exception as e:
            logger.error(f"Erreur lors du déploiement de l'agent {agent_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'un agent
        """
        worker_id = f"agent-{agent_id}"
        
        if worker_id in self.running_agents:
            agent_info = self.running_agents[worker_id]
            
            # Vérifier si le processus est toujours en cours d'exécution
            process = self.agent_processes.get(worker_id)
            if process and process.poll() is not None:
                # Le processus s'est arrêté
                self.running_agents[worker_id]["status"] = "stopped"
            
            return {
                "agent_id": agent_id,
                "worker_id": worker_id,
                "status": self.running_agents[worker_id].get("status", "unknown"),
                "deployed_at": self.running_agents[worker_id].get("deployed_at")
            }
        else:
            return {
                "agent_id": agent_id,
                "worker_id": worker_id,
                "status": "not_found"
            }
    
    async def stop_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Arrête un agent en cours d'exécution
        """
        worker_id = f"agent-{agent_id}"
        
        if worker_id not in self.running_agents:
            return {
                "agent_id": agent_id,
                "status": "not_found"
            }
        
        process = self.agent_processes.get(worker_id)
        if process:
            try:
                # Envoyer un signal d'arrêt au processus
                process.terminate()
                
                # Attendre que le processus se termine
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Si le processus ne se termine pas, le tuer
                    process.kill()
                
                # Mettre à jour le statut
                self.running_agents[worker_id]["status"] = "stopped"
                
                logger.info(f"Agent {worker_id} arrêté avec succès")
                
                return {
                    "agent_id": agent_id,
                    "worker_id": worker_id,
                    "status": "stopped"
                }
            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt de l'agent {worker_id}: {e}")
                return {
                    "status": "error",
                    "error": str(e)
                }
        else:
            # Pas de processus, mais l'agent est enregistré
            self.running_agents[worker_id]["status"] = "not_running"
            
            return {
                "agent_id": agent_id,
                "worker_id": worker_id,
                "status": "not_running"
            }
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        Liste tous les agents
        """
        agents = []
        
        for worker_id, agent_info in self.running_agents.items():
            # Mettre à jour le statut si nécessaire
            process = self.agent_processes.get(worker_id)
            if process and process.poll() is not None:
                agent_info["status"] = "stopped"
            
            agents.append({
                "agent_id": agent_info.get("agent_id"),
                "worker_id": worker_id,
                "name": agent_info.get("name"),
                "status": agent_info.get("status"),
                "deployed_at": agent_info.get("deployed_at")
            })
        
        return agents

# Instancier le service
agent_service = AgentService()
