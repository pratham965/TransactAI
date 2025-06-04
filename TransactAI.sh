#!/bin/bash

(
  cd main/backend || exit
  echo "Starting Python server..."
  python3 backend-server.py
) &

(
  cd main/backend || exit
  echo "Starting ML backend..."
  python3 mlserver.py
) &

(
  cd main/backend || exit
  echo "Starting report backend..."
  python3 reportserver.py
) &


(
  cd main/frontend || exit
  echo "Starting frontend and opening browser..."
  streamlit run main.py
) &

wait
	
