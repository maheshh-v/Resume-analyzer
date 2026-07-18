"""Bulk candidate intake: filename→name derivation, sheet parsing, and resume-URL fetching.

Three ways candidates arrive in bulk — a pile of PDFs, an exported spreadsheet, or a public
apply link — all funneling into the same process_candidate_resume pipeline the single-upload
path uses. Nothing here touches scoring or verdicts; it only creates candidates and hands
their resumes to the existing pipeline.
"""
