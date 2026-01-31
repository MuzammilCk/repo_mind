def unsafe_query(user_input):
    """Intentionally unsafe for CodeQL testing"""
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    return query

def safe_query(user_input):
    """Safe parameterized query"""
    return {"query": "SELECT * FROM users WHERE name = ?", "params": [user_input]}
