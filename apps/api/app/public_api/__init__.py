"""White-label public API: key-authenticated verification for staffing agencies.

Separate from the Supabase-auth recruiter surface — callers authenticate with an API key
(hashed at rest), are rate-limited and quota-limited per key, and get an async verification that
webhooks + a branded PDF when done. Stripe metering is scaffolded here but never charges.
"""
