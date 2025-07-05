from flask import current_app

def format_number(value, format_type=None):
    """Format numbers based on their type.
    
    Args:
        value: The number to format
        format_type: Type of number ('close', 'change_percent', 'score', etc.)
    """
    if value is None:
        return "N/A"
        
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    
    if format_type == 'close':
        return f"{value:,.2f}"
    elif format_type == 'change_percent':
        return f"{value:+.2f}%"
    elif format_type == 'score':
        return f"{value:.2f}"
    else:
        # Default formatting
        if value.is_integer():
            return f"{value:,.0f}"
        return f"{value:,.2f}"

def register_template_filters(app):
    """Register template filters with the Flask app."""
    app.jinja_env.filters['format_number'] = format_number
