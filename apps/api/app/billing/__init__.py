"""Billing scaffold. Records metered usage to Stripe for API keys that opted in — but never
collects card details and never charges anything on its own. Onboarding a customer (creating the
Stripe customer + meter) is a manual, out-of-band step; this only emits usage events.
"""
