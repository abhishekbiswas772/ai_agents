import tiktoken

def get_tokenizer(model: str):
    try:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.encode
    except Exception as e:
        encoding = tiktoken.get_encoding("cl100k_base")
        return encoding.encode


def count_token(text: str, model: str) -> int:
    tokenizer = get_tokenizer(model)
    if tokenizer:
        return len(tokenizer(text))
    return estimate_token(text=text)
    
def estimate_token(text: str) -> str:
    return max(1, len(text) // 4)


def truncate_text(
    text : str,
    model : str,
    max_tokens: int,
    suffix : str = "\n...[truncated]",
    preserve_lines: bool = True
):
    current_token = count_token(text, model)
    if current_token <= max_tokens:
        return text
    suffix_tokens = count_token(suffix, model)
    target_token = max_tokens - suffix_tokens

    if target_token <= 0:
        return suffix.strip()
    
    if preserve_lines:
        pass


def _truncate_by_lines(text: str, target_tokens: int, suffix: str, model: str) -> str:
    pass

def _truncate_by_chars(text: str, target_tokens: int, suffix: str, model: str) -> str:
    low = 0
    high = len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if count_token(text[:mid], model) <= target_tokens:
            low = mid
        else:
            high = mid - 1
    return text[:low] + suffix
