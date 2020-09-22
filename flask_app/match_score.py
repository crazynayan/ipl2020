from firestore_ci import FirestoreDocument

from config import Config


class MatchScores(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.player_name: str = str()
        self.team: str = str()
        self.match_id: str = str()
        self.owner: str = str()
        self.gameweek: int = int()
        self.type: str = Config.NORMAL
        self.runs: int = int()
        self.fours: int = int()
        self.sixes: int = int()
        self.batting_points: int = int()
        self.overs: float = float()
        self.wickets: int = int()
        self.economy_rate: float = float()
        self.bowling_points: int = int()
        self.man_of_the_match: bool = bool()
        self.points: int = int()


MatchScores.init("match_scores")
