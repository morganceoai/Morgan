#!/bin/bash
cd /Users/bcvertex/Morgan
source venv/bin/activate
nohup python telegram_bot.py >> /Users/bcvertex/Morgan/memory/morgan.log 2>&1 &
