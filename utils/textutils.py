def trunc_text(text, max_len):
    """
    Truncate text to max of a number chars and add ellipsis if text is longer
    """
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    else:
        return text