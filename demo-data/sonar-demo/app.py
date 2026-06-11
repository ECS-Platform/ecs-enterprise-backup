"""ECS SonarQube demo application.

Intentionally contains code-quality and security issues so the SonarQube
analysis produces vulnerabilities, hotspots, bugs, and code smells for ECS to
collect as evidence. DO NOT use any of this in production.
"""

import hashlib
import sqlite3


# Security hotspot: hardcoded credentials.
DB_PASSWORD = "SuperSecret123!"
API_TOKEN = "ghp_demohardcodedtoken0000000000000000"


def login(username, password):
    # Vulnerability: SQL injection via string concatenation.
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + username + "' AND pw = '" + password + "'"
    cur.execute(query)
    return cur.fetchone()


def weak_hash(value):
    # Security hotspot: weak hashing algorithm (MD5).
    return hashlib.md5(value.encode()).hexdigest()


def unused_calculation(items):
    # Code smell: unused variable and dead code.
    total = 0
    count = 0
    for item in items:
        total += item
    return total


def duplicated_block_one(data):
    result = []
    for d in data:
        if d is not None:
            result.append(d * 2)
    return result


def duplicated_block_two(data):
    result = []
    for d in data:
        if d is not None:
            result.append(d * 2)
    return result
