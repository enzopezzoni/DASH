from datetime import datetime

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def to_date(value):
    """Convert string to date"""
    return datetime.strptime(value, '%Y-%m-%d')