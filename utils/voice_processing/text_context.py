import logging
from typing import Optional, Set, Tuple

logger = logging.getLogger(__name__)

class TextContext:
    """
    Extracts meaningful text segments (contexts) from a given string.

    This class identifies substrings that end with predefined split tokens,
    adhere to specified length constraints, and contain a minimum number
    of alphanumeric characters.
    """
    def __init__(self, split_tokens: Optional[Set[str]] = None) -> None:
        """
        Initializes the TextContext processor.

        Args:
            split_tokens: An optional set of strings. Each string is treated as a
                          potential end-of-context marker. If None, a default set
                          of punctuation and whitespace characters is used.
        """
        if split_tokens is None:
            # Using a more explicit variable name internally for clarity
            default_splits: Set[str] = {".", "!", "?", ",", ";", ":", "\n", "-", "。", "、"}
            self.split_tokens: Set[str] = default_splits
        else:
            self.split_tokens: Set[str] = set(split_tokens)

    def get_context(self, txt: str, min_len: int = 6, max_len: int = 120, min_alnum_count: int = 10) -> Tuple[Optional[str], Optional[str]]:
        """
        Finds the shortest valid context at the beginning of the input text.

        Args:
            txt: The input string from which to extract the context.
            min_len: The minimum allowable overall length for the extracted context substring.
            max_len: The maximum allowable overall length for the extracted context substring.
            min_alnum_count: The minimum number of alphanumeric characters required.

        Returns:
            A tuple containing:
            - The extracted context string if found, otherwise None.
            - The remaining part of the input string after the context, otherwise None.
        """
        alnum_count = 0

        for i in range(1, min(len(txt), max_len) + 1):
            char = txt[i - 1]
            if char.isalnum():
                alnum_count += 1

            # Check if the current character is a potential context end
            if char in self.split_tokens:
                # Check if length and alphanumeric count criteria are met
                if i >= min_len and alnum_count >= min_alnum_count:
                    context_str = txt[:i]
                    remaining_str = txt[i:]
                    logger.info(f"🧠 Context found after char no: {i}, context: {context_str}")
                    return context_str, remaining_str

        # No suitable context found within the max_len limit
        return None, None
