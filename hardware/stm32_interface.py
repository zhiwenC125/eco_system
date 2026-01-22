import serial
import time
import struct # 核心：用于二进制打包解析

class STM32Interface:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200):
        try:
            # 设置较短的 timeout，防止请求无响应时阻塞 Web 主线程
            self.ser = serial.Serial(port, baudrate, timeout=0.5)
            self.ser.flush()
            print(f"✅ 串口对齐接口已就绪: {port}")
        except Exception as e:
            print(f"❌ 串口连接失败: {e}")
            self.ser = None

    def get_realtime_data(self, student_id_str):
        """
        [进化版] 带有二进制协议握手的数据请求函数
        """
        if not self.ser:
            return None

        try:
            # 1. 协议预处理：将学号末尾转为 2 字节整数（模拟学号后 4 位）
            try:
                s_id_int = int(student_id_str[-4:])
            except:
                s_id_int = 0

            # 2. 构造【发送请求帧】
            # 格式：[帧头 0xAA] [指令 0x01] [学号L] [学号H] [帧尾 0x55]
            # <BBHB 代表：小端、1字节、1字节、2字节(无符号短整型)、1字节
            req_frame = struct.pack('<BBHB', 0xAA, 0x01, s_id_int, 0x55)
            
            # 清除缓冲区旧数据，确保拿到的是针对本次请求的新鲜采样
            self.ser.reset_input_buffer()
            self.ser.write(req_frame)
            
            # 3. 等待 STM32 采样并回传（响应时间约 50-100ms）
            time.sleep(0.1) 

            # 4. 读取【响应帧】并解析
            # 期望格式：[帧头 0xBB] [电力L] [电力H] [水流L] [水流H] [帧尾 0x55]
            if self.ser.in_waiting >= 6:
                raw_resp = self.ser.read(6)
                header, elec_raw, water_raw, footer = struct.unpack('<BHHB', raw_resp)
                
                # 5. 帧校验：首尾检查确保数据完整性
                if header == 0xBB and footer == 0x55:
                    # 假设单片机端将浮点数放大了 100 倍以整数传输
                    return {
                        "electricity": elec_raw / 100.0,
                        "hot_water": water_raw / 100.0
                    }
                else:
                    print("⚠️ 帧校验失败，数据可能受到干扰")
            
        except Exception as e:
            print(f"❌ 串口对齐事务失败: {e}")
        
        # 如果通信失败，返回 None，由后端使用兜底逻辑
        return None

if __name__ == "__main__":
    # 测试代码
    hw = STM32Interface()
    test_id = "20240001"
    while True:
        data = hw.get_realtime_data(test_id)
        if data: 
            print(f"成功对齐 [ID:{test_id}] 硬件数据: {data}")
        else:
            print("正在等待 STM32 响应...")
        time.sleep(2)