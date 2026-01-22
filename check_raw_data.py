import serial
import struct
import time

# 初始化串口 (确保端口与树莓派5一致，通常为 /dev/ttyAMA0)
try:
    ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
    ser.flush()
    print("✅ 串口已开启，准备测试硬件对齐...")
except Exception as e:
    print(f"❌ 开启串口失败: {e}")
    exit()

def test_hardware_link():
    # 1. 构造请求帧 [帧头, 指令, ID低位, ID高位, 帧尾]
    # 我们发送 0xAA 0x01 以及模拟学号 2518 (0x09D6)
    request_frame = struct.pack('<BBHB', 0xAA, 0x01, 2518, 0x55)
    
    while True:
        print(f"\n发送请求帧: {request_frame.hex().upper()}")
        ser.reset_input_buffer()
        ser.write(request_frame)
        
        # 2. 等待响应 (STM32 中断处理约需几毫秒)
        time.sleep(0.1)
        
        if ser.in_waiting >= 6:
            raw_data = ser.read(6)
            print(f"收到原始十六进制: {raw_data.hex().upper()}")
            
            # 3. 解析 6 字节二进制帧 [0xBB, Elec_L, Elec_H, Water_L, Water_H, 0x55]
            # <BHHB 代表: 1字节, 2字节无符号短整型, 2字节无符号短整型, 1字节
            try:
                header, elec_raw, water_raw, tail = struct.unpack('<BHHB', raw_data)
                
                if header == 0xBB and tail == 0x55:
                    # 还原 100 倍缩放
                    elec = elec_raw / 100.0
                    water = water_raw / 100.0
                    print(f"解析结果成功！ -> 用电: {elec} kWh, 用水: {water} L")
                else:
                    print("⚠️ 帧校验失败 (头或尾不匹配)")
            except Exception as e:
                print(f"❌ 解析出错: {e}")
        else:
            print("❌ 未收到硬件响应。请检查：1. STM32是否烧录最新代码 2. TX/RX接线 3. 是否共地")
        
        time.sleep(1)

if __name__ == "__main__":
    test_hardware_link()