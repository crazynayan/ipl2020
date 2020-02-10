from typing import Optional

from firestore_ci import FirestoreDocument

from flask_app import ipl_app


class Player(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.name: str = str()
        self.cost: int = 0
        self.base: int = 0
        self.country: str = str()
        self.type: str = str()
        self.ipl2019_score: float = 0.0
        self.team: str = str()
        self.owner: Optional[str] = None
        self.price: int = 0
        self.score: float = 0.0
        self.ipl2019_rank: int = 0
        self.cost_rank: int = 0

    @property
    def image(self) -> str:
        file_name = f"{self.name.lower().replace(' ', '_')}.jpg"
        if file_name not in ipl_app.config['IMAGES']:
            file_name = 'default.jpg'
        return f'images/{file_name}'


Player.init()
