from typing import Optional

from firestore_ci import FirestoreDocument


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


Player.init()
