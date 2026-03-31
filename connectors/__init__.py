"""
connectors/ — Secure real-world action connectors.

Each connector:
  - Respects policy layer
  - Produces ExecutionTrace
  - Is disableable via env var
  - Fail-open: never crashes caller
"""
