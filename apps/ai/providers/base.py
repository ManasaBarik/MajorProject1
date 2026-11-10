from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def analyze_complaint(self, complaint):
        raise NotImplementedError
