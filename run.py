
import uvicorn

from app.main import app 
# Fonction pour exécuter Uvicorn
def run_uvicorn():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port =8007,
        reload= False,
    )


# Exécution du serveur selon la configuration
if __name__ == "__main__":
    run_uvicorn()

