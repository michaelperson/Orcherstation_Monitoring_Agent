#!/usr/bin/env bash
# preparer_poste.sh : prérequis SYSTÈME d'un poste de la salle, à lancer UNE fois par un administrateur,
# AVANT installer_reseau.sh. Ubuntu 24.04, Docker Engine (paquets docker-ce, pas le snap), pilote NVIDIA ≥ 580.
#
#   sudo bash infrastructure/preparer_poste.sh                    # le compte qui lance sudo
#   sudo bash infrastructure/preparer_poste.sh stagiaire1 stagiaire2   # ou les comptes des apprenants
#
# 1. NVIDIA Container Toolkit (dépôt NVIDIA, version figée) : sans lui, Docker ne voit pas le GPU et vLLM
#    échoue au démarrage, APRÈS ≈ 28 Go de téléchargement.
# 2. Runtime Docker configuré (nvidia-ctk), puis redémarrage de Docker : les conteneurs en cours s'arrêtent.
# 3. Comptes ajoutés au groupe docker : sinon « permission denied » sur /var/run/docker.sock.
#    ⚠️ Le groupe docker équivaut à un accès root sur le poste : à réserver aux postes de formation.
# 4. Vérification : un conteneur voit le GPU.
#
# Relançable : ne refait que ce qui manque. Procédure NVIDIA vérifiée le 30/10/2026 (toolkit 1.20.1-1).
set -euo pipefail

NCT_VERSION=1.20.1-1
DEPOT=https://nvidia.github.io/libnvidia-container
TROUSSEAU=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
LISTE=/etc/apt/sources.list.d/nvidia-container-toolkit.list

[[ $EUID -eq 0 ]] || { echo "À lancer en administrateur : sudo bash $0 [utilisateur ...]"; exit 1; }
COMPTES=("$@")
(( ${#COMPTES[@]} )) || COMPTES=("${SUDO_USER:?précisez le ou les comptes : sudo bash $0 <utilisateur> ...}")

echo "== 1/4 Contrôles"
command -v docker >/dev/null || { echo "❌ Docker absent : installer Docker Engine (docs.docker.com/engine/install/ubuntu)"; exit 1; }
if command -v snap >/dev/null && snap list docker >/dev/null 2>&1; then
  echo "❌ Docker est installé en snap : le Container Toolkit ne s'y configure pas. Installer Docker Engine (docker-ce)."
  exit 1
fi
if ! nvidia-smi >/dev/null 2>&1; then
  echo "❌ nvidia-smi ne répond pas : installer le pilote NVIDIA (≥ 580), redémarrer le poste, puis relancer ce script."
  exit 1
fi
PILOTE=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | cut -d. -f1)
(( PILOTE >= 580 )) || echo "⚠️  pilote NVIDIA $PILOTE < 580 : le toolkit s'installe, mais l'image vLLM (CUDA 13) ne démarrera pas."
for compte in "${COMPTES[@]}"; do
  id "$compte" >/dev/null 2>&1 || { echo "❌ compte inconnu : $compte"; exit 1; }
done

echo "== 2/4 NVIDIA Container Toolkit $NCT_VERSION"
if command -v nvidia-ctk >/dev/null; then
  echo "déjà installé : $(nvidia-ctk --version | head -1)"
else
  apt-get update
  apt-get install -y --no-install-recommends ca-certificates curl gnupg2
  curl -fsSL "$DEPOT/gpgkey" | gpg --dearmor --yes -o "$TROUSSEAU"
  curl -fsSL "$DEPOT/stable/deb/nvidia-container-toolkit.list" \
    | sed "s#deb https://#deb [signed-by=$TROUSSEAU] https://#g" > "$LISTE"
  apt-get update
  apt-get install -y \
    "nvidia-container-toolkit=$NCT_VERSION" "nvidia-container-toolkit-base=$NCT_VERSION" \
    "libnvidia-container-tools=$NCT_VERSION" "libnvidia-container1=$NCT_VERSION"
fi
nvidia-ctk runtime configure --runtime=docker   # écrit /etc/docker/daemon.json (idempotent)
systemctl restart docker

echo "== 3/4 Groupe docker"
AJOUTES=()
for compte in "${COMPTES[@]}"; do
  if id -nG "$compte" | tr ' ' '\n' | grep -qx docker; then
    echo "$compte : déjà dans le groupe docker"
  else
    usermod -aG docker "$compte"
    AJOUTES+=("$compte")
    echo "$compte : ajouté au groupe docker"
  fi
done

echo "== 4/4 Vérification : un conteneur voit-il le GPU ?"
if docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L; then
  echo "✅ poste prêt pour installer_reseau.sh"
else
  echo "❌ Docker ne voit pas le GPU : voir /etc/docker/daemon.json et « journalctl -u docker »"
  exit 1
fi
if (( ${#AJOUTES[@]} )); then
  echo "⚠️  ${AJOUTES[*]} : fermer la session et se reconnecter (ou redémarrer) pour que le groupe docker s'applique."
fi
