import os


class LocustfileStorage:
    def upload(self, locustfile: os.PathLike) -> None:
        raise NotImplementedError()

    def delete(self) -> None:
        raise NotImplementedError()
