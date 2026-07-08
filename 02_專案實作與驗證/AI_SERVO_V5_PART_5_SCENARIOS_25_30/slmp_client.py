#!/usr/bin/env python3
import socket
import struct
import threading
import time
import numpy as np

class SLMPClient:
    """
    三菱 MC Protocol (3E Binary Frame) 實體通信客戶端
    """
    PARAMETER_MAP = {
        "PE02": 1002,
        "PE07": 1007,
        "PA09": 1009,
        "PA11": 1011,
        "PB12": 1012,
        "PA12": 1052,
        "PA18": 1018,
        "PB07": 1027,
        "PB08": 1028,
        "PB09": 1029,
        "PC16": 1056,
        "PC24": 1064,
    }

    def __init__(self, host="127.0.0.1", port=5007):
        self.host = host
        self.port = port
        self.sock = None

    def write_mr_j5_parameter(self, param_name, value, network_no=0x00, pc_no=0xFF, dest_io=0x03FF, dest_station=0x00):
        if param_name not in self.PARAMETER_MAP:
            raise ValueError(f"Unknown parameter name: {param_name}")
        addr = self.PARAMETER_MAP[param_name]
        return self.write_d_registers(addr, [int(value)], network_no, pc_no, dest_io, dest_station)

    def read_mr_j5_parameter(self, param_name, network_no=0x00, pc_no=0xFF, dest_io=0x03FF, dest_station=0x00):
        if param_name not in self.PARAMETER_MAP:
            raise ValueError(f"Unknown parameter name: {param_name}")
        addr = self.PARAMETER_MAP[param_name]
        res = self.read_d_registers(addr, 1, network_no, pc_no, dest_io, dest_station)
        return res[0] if res else None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2.0)
        self.sock.connect((self.host, self.port))

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _build_header(self, request_length, network_no=0x00, pc_no=0xFF, dest_io=0x03FF, dest_station=0x00):
        # Header (2 bytes) = 0x50, 0x00 (Request)
        # Network No (1 byte)
        # PC No (1 byte)
        # Destination I/O No (2 bytes)
        # Destination Station No (1 byte)
        # Request Data Length (2 bytes) = request_length (little-endian)
        # CPU Monitor Timer (2 bytes) = 0x10, 0x00 (4 seconds, little-endian)
        return struct.pack("<HBBHBH", 0x5000, network_no, pc_no, dest_io, dest_station, request_length) + b"\x10\x00"

    def read_d_registers(self, start_addr, points, network_no=0x00, pc_no=0xFF, dest_io=0x03FF, dest_station=0x00):
        """
        批次讀取 D 暫存器 (MC 3E Batch Read command: 0x0401)
        支援多站點 TSN 路由與特定網路 ID
        """
        request_body = struct.pack("<HH", 0x0401, 0x0000)
        addr_bytes = struct.pack("<I", start_addr)[:3]
        request_body += addr_bytes + b"\xA8" + struct.pack("<H", points)
        
        request_length = len(request_body)
        packet = self._build_header(request_length, network_no, pc_no, dest_io, dest_station) + request_body
        
        self.sock.sendall(packet)
        response = self.sock.recv(1024)
        return self._parse_read_response(response, points)

    def write_d_registers(self, start_addr, values, network_no=0x00, pc_no=0xFF, dest_io=0x03FF, dest_station=0x00):
        """
        批次寫入 D 暫存器 (MC 3E Batch Write command: 0x1401)
        支援多站點 TSN 路由與特定網路 ID
        """
        points = len(values)
        request_body = struct.pack("<HH", 0x1401, 0x0000)
        addr_bytes = struct.pack("<I", start_addr)[:3]
        request_body += addr_bytes + b"\xA8" + struct.pack("<H", points)
        
        for val in values:
            request_body += struct.pack("<h", val)
            
        request_length = len(request_body)
        packet = self._build_header(request_length, network_no, pc_no, dest_io, dest_station) + request_body
        
        self.sock.sendall(packet)
        response = self.sock.recv(1024)
        return self._parse_write_response(response)

    def check_anti_chatter_current(self, current_samples, window_size=3, threshold=15.0):
        """
        實施改善計畫：防抖濾波器 (Anti-Chatter Filter)
        計算滑動平均以防單點電流雜訊瞬時超限觸發誤回滾
        """
        if len(current_samples) < window_size:
            return np.mean(current_samples) > threshold
        for i in range(len(current_samples) - window_size + 1):
            window = current_samples[i:i+window_size]
            if np.mean(window) > threshold:
                return True
        return False

    def _parse_read_response(self, response, points):
        # 3E Response structure:
        # Subheader (2 bytes) = 0x00D0 (Response from PLC)
        # Network No, PC No, Dest I/O, Dest Station = 5 bytes
        # Response Data Length (2 bytes)
        # End Code (2 bytes) = 0x0000 (Success)
        # Data (2 * points bytes)
        if len(response) < 11:
            raise ValueError("Response packet too short")
        
        subheader, network_no, pc_no, dest_io, dest_station, data_len = struct.unpack("<HBBHBH", response[:9])
        end_code = struct.unpack("<H", response[9:11])[0]
        
        if end_code != 0:
            raise RuntimeError(f"SLMP Response returned error code: {end_code:#06x}")
            
        data = []
        offset = 11
        for _ in range(points):
            val = struct.unpack("<h", response[offset:offset+2])[0]
            data.append(val)
            offset += 2
        return data

    def _parse_write_response(self, response):
        if len(response) < 11:
            raise ValueError("Response packet too short")
        subheader, network_no, pc_no, dest_io, dest_station, data_len = struct.unpack("<HBBHBH", response[:9])
        end_code = struct.unpack("<H", response[9:11])[0]
        return end_code == 0

class SLMPServerMock:
    """
    三菱 MC Protocol (3E Binary Frame) 模擬通訊伺服器
    """
    def __init__(self, host="127.0.0.1", port=5007):
        self.host = host
        self.port = port
        self.registers = {
            1002: 10,  # PE02 default
            1007: 0,   # PE07 default
            1009: 12,  # PA09 default
            1011: 300, # PA11 default
            1012: 0,   # PB12 default
            1052: 300, # PA12 default
            1018: 0,   # PA18 default
            1027: 100, # PB07 default
            1028: 150, # PB08 default
            1029: 20,  # PB09 default
            1056: 50,  # PC16 default
            1064: 100, # PC24 default
            1010: 0    # Speed register
        }
        self.running = False
        self.sock = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.running = True
        
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def _server_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, conn):
        conn.settimeout(2.0)
        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                
                # 解析 3E Request Header
                subheader, network_no, pc_no, dest_io, dest_station, req_len = struct.unpack("<HBBHBH", data[:9])
                timer = struct.unpack("<H", data[9:11])[0]
                command, subcmd = struct.unpack("<HH", data[11:15])
                
                # 解析地址與點數
                addr_bytes = data[15:18] + b"\x00"
                start_addr = struct.unpack("<I", addr_bytes)[0]
                device_code = data[18]
                points = struct.unpack("<H", data[19:21])[0]
                
                response_body = b""
                end_code = 0x0000
                
                if command == 0x0401: # Read
                    for i in range(points):
                        addr = start_addr + i
                        val = self.registers.get(addr, 0)
                        response_body += struct.pack("<h", val)
                elif command == 0x1401: # Write
                    offset = 21
                    for i in range(points):
                        addr = start_addr + i
                        val = struct.unpack("<h", data[offset:offset+2])[0]
                        self.registers[addr] = val
                        offset += 2
                else:
                    end_code = 0xC0C0 # 不支援的命令
                    
                # 建立 Response
                # Response subheader = 0x0080
                res_len = 2 + len(response_body) # end_code (2 bytes) + data
                response_header = struct.pack("<HBBHBH", 0x0080, network_no, pc_no, dest_io, dest_station, res_len)
                response = response_header + struct.pack("<H", end_code) + response_body
                conn.sendall(response)
                
            except Exception:
                break
        conn.close()
