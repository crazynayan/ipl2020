from typing import Dict, List, Tuple

from firestore_ci import FirestoreDocument

from config import Config


class ScoreData:

    def __init__(self, score_data: Dict):
        self.score_data = score_data

    def get_value(self, pid: str, key: str, score_type: str) -> float:
        player_record = next((player for team in self.score_data[score_type] for player in team["scores"]
                              if player["pid"] == pid), dict())
        if not player_record or key not in player_record:
            return 0.0
        try:
            value = float(player_record[key])
        except ValueError:
            value = 0.0
        return value

    def get_runs(self, pid: str) -> int:
        return int(self.get_value(pid, "R", "batting"))

    def get_fours(self, pid: str) -> int:
        return int(self.get_value(pid, "4s", "batting"))

    def get_sixes(self, pid: str) -> int:
        return int(self.get_value(pid, "6s", "batting"))

    def get_overs(self, pid: str) -> float:
        return self.get_value(pid, "O", "bowling")

    def get_wickets(self, pid: str) -> int:
        return int(self.get_value(pid, "W", "bowling"))

    def get_economy_rate(self, pid: str) -> float:
        return self.get_value(pid, "Econ", "bowling")

    def get_man_of_the_match(self, pid: str) -> bool:
        if "man-of-the-match" not in self.score_data:
            return False
        if "pid" not in self.score_data["man-of-the-match"]:
            return False
        if pid != self.score_data["man-of-the-match"]["pid"]:
            return False
        return True

    def get_playing_xi(self) -> List[Tuple[str, str]]:
        return [(player["pid"], player["name"]) for team in self.score_data["team"] for player in team["players"]]


class MatchPlayer(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.player_id: str = str()
        self.player_name: str = str()
        self.team: str = str()
        self.match_id: str = str()
        self.owner: str = str()
        self.gameweek: int = int()
        self.type: str = Config.NORMAL
        self.runs: int = int()
        self.fours: int = int()
        self.sixes: int = int()
        self.overs: float = float()
        self.wickets: int = int()
        self.economy_rate: float = float()
        self.man_of_the_match: bool = bool()

    @property
    def batting_points(self) -> int:
        score = self.runs + self.fours * 2 + self.sixes * 3
        if self.runs >= 50:
            score += 10
        if self.runs >= 100:
            score += 20
        return score

    @property
    def bowling_points(self) -> int:
        score = self.wickets * 20
        if not self.overs:
            return score
        if self.economy_rate < 2.0:
            score += 50
        elif self.economy_rate < 4.0:
            score += 40
        elif self.economy_rate < 6.0:
            score += 30
        elif self.economy_rate < 7.0:
            score += 20
        return score

    @property
    def man_of_the_match_points(self) -> int:
        return 50 if self.man_of_the_match else 0

    @property
    def total_points(self):
        return self.batting_points + self.bowling_points + self.man_of_the_match_points

    @property
    def adjusted_points(self) -> float:
        if self.type == Config.CAPTAIN:
            return float(self.total_points * 2)
        elif self.type == Config.SUB:
            return self.total_points / 2
        return float(self.total_points)

    @property
    def display_class(self) -> str:
        if self.type == Config.CAPTAIN:
            return "table-success"
        elif self.type == Config.SUB:
            return "table-danger"
        return str()

    @property
    def owner_full_name(self) -> str:
        return Config.USER_LIST.get(self.owner.upper(), str())

    def update_scores(self, score_data: ScoreData):
        self.runs = score_data.get_runs(self.player_id)
        self.fours = score_data.get_fours(self.player_id)
        self.sixes = score_data.get_sixes(self.player_id)
        self.wickets = score_data.get_wickets(self.player_id)
        self.economy_rate = score_data.get_economy_rate(self.player_id)
        self.overs = score_data.get_overs(self.player_id)
        self.man_of_the_match = score_data.get_man_of_the_match(self.player_id)


MatchPlayer.init("match_players")
