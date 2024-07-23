set root=C:\Users\WinUser\miniconda3

call %root%\Scripts\activate.bat %root%

call conda list pandas

call conda activate yolo

yolo segment train data=./data.yaml model=yolov8m-seg.pt


pause 