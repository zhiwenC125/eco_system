import serial
import time

# 开启串口
ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)

while True:
    # 发送请求帧：[0xAA, 0x01, 0x00, 0x00, 0x55]
    print("发送请求...")
    ser.write(b'\xAA\x01\x00\x00\x55')
    
    # 等待 0.2 秒看有没有回传
    time.sleep(0.2)
    if ser.in_waiting > 0:
        data = ser.read(ser.in_waiting)
        print(f"收到硬件原始字节: {data.hex()}")
    else:
        print("未收到任何响应，请检查 STM32 是否供电或接线是否反了")
    time.sleep(1)