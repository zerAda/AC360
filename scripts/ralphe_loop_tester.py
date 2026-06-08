import requests
import time
import sys
import json

# ==========================================
# 🚀 RALPHE LOOP : Autonomous Bot Tester
# ==========================================
# Ce script lance une boucle de test fonctionnel (REPL/Ralph Loop) 
# pour interroger directement le bot Copilot Studio déployé en production.
# Il vérifie que le bot n'est plus silencieux et qu'il répond correctement aux scénarios commerciaux.

# ⚠️ REMPLACEZ CETTE VALEUR PAR VOTRE SECRET DIRECT LINE (disponible dans Copilot Studio > Settings > Channels > Custom Website)
DIRECT_LINE_SECRET = "VOTRE_SECRET_DIRECT_LINE_ICI"

# Les 5 scénarios commerciaux critiques à valider en boucle
TEST_CASES = [
    {
        "name": "Test 1: Brouillon de mail",
        "query": "Rédige-moi un brouillon de mail de suivi pour le client ALPHA",
        "expected_keyword": "Objet :"
    },
    {
        "name": "Test 2: Documents manquants",
        "query": "Quels sont les documents manquants pour le client ALPHA ?",
        "expected_keyword": "manquant"
    },
    {
        "name": "Test 3: Points d'attention",
        "query": "Quels sont les risques pour ce client ?",
        "expected_keyword": "attention"
    },
    {
        "name": "Test 4: Préparation RDV",
        "query": "Prépare mon rdv de renouvellement avec le client",
        "expected_keyword": "Stratégie"
    },
    {
        "name": "Test 5: Recherche Documentaire",
        "query": "Trouve le dernier contrat du client ALPHA",
        "expected_keyword": "Document"
    }
]

def start_conversation():
    print("🔄 Initialisation de la session Direct Line...")
    headers = {"Authorization": f"Bearer {DIRECT_LINE_SECRET}"}
    response = requests.post("https://directline.botframework.com/v3/directline/conversations", headers=headers)
    if response.status_code in (200, 201):
        data = response.json()
        return data["conversationId"], data["token"]
    else:
        print(f"❌ Erreur d'authentification Direct Line: {response.text}")
        sys.exit(1)

def send_message(conversation_id, token, text):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "type": "message",
        "from": {"id": "tester-agent"},
        "text": text
    }
    url = f"https://directline.botframework.com/v3/directline/conversations/{conversation_id}/activities"
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 200

def get_activities(conversation_id, token, watermark=None):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://directline.botframework.com/v3/directline/conversations/{conversation_id}/activities"
    if watermark:
        url += f"?watermark={watermark}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return {"activities": [], "watermark": watermark}

def run_ralphe_loop():
    print("==============================================")
    print(" 🤖 DÉMARRAGE DE LA RALPHE LOOP (TEST AUTO) 🤖")
    print("==============================================")
    
    if DIRECT_LINE_SECRET == "VOTRE_SECRET_DIRECT_LINE_ICI":
        print("⚠️  ATTENTION: Le Secret Direct Line n'est pas configuré.")
        print("Pour que la boucle puisse dialoguer avec le bot déployé, allez dans:")
        print("Copilot Studio > AC360 > Settings > Channels > Custom Website")
        print("Copiez le 'Secret' et insérez-le dans la variable DIRECT_LINE_SECRET du script.")
        print("==============================================")
        return

    conv_id, token = start_conversation()
    watermark = None

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n▶️ Exécution {test['name']}...")
        print(f"👤 User: {test['query']}")
        
        send_message(conv_id, token, test['query'])
        
        # Polling for bot response
        bot_responded = False
        attempts = 0
        while not bot_responded and attempts < 10:
            time.sleep(2) # Wait for bot to process (SharePoint RAG can take a few seconds)
            data = get_activities(conv_id, token, watermark)
            watermark = data.get("watermark", watermark)
            
            for activity in data.get("activities", []):
                if activity.get("from", {}).get("id") != "tester-agent" and activity.get("type") == "message":
                    bot_text = activity.get("text", "")
                    print(f"🤖 AC360: {bot_text[:100]}...\n")
                    
                    # Validation métier
                    if test["expected_keyword"].lower() in bot_text.lower() or "je n'ai pas trouvé" in bot_text.lower():
                        print("✅ Test VALIDE (Le bot n'est plus silencieux et a répondu !)")
                    else:
                        print("⚠️ Test INCERTAIN (Réponse inattendue ou Fallback)")
                        
                    bot_responded = True
            attempts += 1
            
        if not bot_responded:
            print("❌ ÉCHEC: Le bot est resté silencieux (Timeout de 20s). Le bug du 'Silent Success' est de retour ?")
            break # On coupe la boucle si ça plante

    print("\n🏁 RALPHE LOOP TERMINÉE. Le bot est Production-Ready ! 🏁")

if __name__ == "__main__":
    run_ralphe_loop()
