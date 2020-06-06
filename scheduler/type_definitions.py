from typing import Optional, List
import uuid


class Package:
    name: str
    dependency: Optional[List[Package]]


class Job:
    name: str
    uuid: uuid.UUID
    description: str
    packages: List[Package]
    architecture: List[str]

    # The actual build sequence, after processed by PreProcessors.
    build_packages: List[Package]
    postbuild: List[Package]

    def __init__(self, name: str, description: str, packages: List[Package],
                 architecture: List[str]):
        self.name = name
        self.uuid = uuid.uuid4()
        self.description = description
        self.packages = packages
        self.architecture = architecture

        self.build_packages = []
        self.postbuild = []
