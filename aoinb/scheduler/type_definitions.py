from typing import Optional, List
import uuid


class Package:
    name: str
    version: str
    dependency: Optional[List[Package]]


class Job:
    name: str
    uuid: uuid.UUID
    description: str
    packages: List[Package]
    architecture: List[str]

    # The actual build sequence, after processed by PreProcessors.
    build_packages: List[Package]
    # A package that contains multiple sub-packages. (See LLVM for example)
    # Sub-packages must be built inside the same working diretory.
    sub_package: List[Package]
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
