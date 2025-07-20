import re
import uuid


def remove_md_asterisks(text):
    """
    Removes markdown asterisk formatting from text while preserving the content.
    Handles both bold (**) and italic (*) formatting.

    Args:
        text (str): Input text containing markdown asterisk formatting

    Returns:
        str: Text with asterisk formatting removed

    Examples:
        >>> remove_md_asterisks("This is **bold** and *italic* text")
        'This is bold and italic text'
    """
    # Remove bold (double asterisks)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # Remove italic (single asterisks)
    text = re.sub(r'\*([^\*]+?)\*', r'\1', text)

    return text


