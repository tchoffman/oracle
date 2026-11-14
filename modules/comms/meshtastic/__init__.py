"""Pergamon's Meshtastic bridge.

Lets a Meshtastic node send a DM to the pergamon and receive a RAG-synthesized
answer back over LoRa. Real hardware mode talks to a USB-connected node;
mock mode reads questions from stdin so you can develop without a radio.
"""
