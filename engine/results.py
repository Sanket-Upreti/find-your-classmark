""" 
    the shapes an answer comes back in;
    every interface (terminal, window, web page) is handed one of these and decides how to say it
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ClassPlacement:
    """ one class, and where it is; location is None when no location is recorded for it """
    classmark: str
    location: str | None = None

@dataclass(frozen=True)
class ClassSubjects:
    """ one class, and every subject taught on it """
    classmark: str
    subjects: tuple[str, ...] = ()

@dataclass(frozen=True)
class SubjectResult:
    """ the answer to 'where does this subject happen' """
    query: str
    placements: tuple[ClassPlacement, ...] = ()

    @property
    def found(self):
        return bool(self.placements)

@dataclass(frozen=True)
class ClassmarkResult:
    """ the answer to 'what is this class, and where' """
    query: str
    locations: tuple[str, ...] = ()
    subjects: tuple[str, ...] = ()

@dataclass(frozen=True)
class LocationResult:
    """ the answer to 'what happens in this location'; location is None when the choice was not valid """
    query: object
    location: str | None = None
    classes: tuple[ClassSubjects, ...] = ()
