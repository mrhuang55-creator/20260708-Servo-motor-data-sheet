#!/usr/bin/env python3
import numpy as np

def sigmoid(x):
    # 數值穩定性防護：clip 防止 exp 溢位 (Numerical Stability Guard)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def softmax(x):
    # 穩定版 Softmax：使用 LogSumExp 技巧 (Stabilized via LogSumExp)
    x_shifted = x - np.max(x, axis=-1, keepdims=True)
    e_x = np.exp(np.clip(x_shifted, -500, 500))
    return e_x / (np.sum(e_x, axis=-1, keepdims=True) + 1e-12)

class NumPyMLP:
    """
    NumPy 實作之極輕量多層感知機 (MLP)
    架構: Input -> Hidden 1 (64, ReLU) -> Hidden 2 (32, ReLU) -> Output (12, Softmax)
    """
    def __init__(self, input_dim=4, hidden1=64, hidden2=32, output_dim=12, lr=0.01):
        self.lr = lr
        # Xavier/He 初始化
        self.W1 = np.random.randn(input_dim, hidden1) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, hidden1))
        self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros((1, hidden2))
        self.W3 = np.random.randn(hidden2, output_dim) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros((1, output_dim))
        
    def forward(self, X):
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = np.maximum(0, self.z1) # ReLU
        
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = np.maximum(0, self.z2) # ReLU
        
        self.z3 = np.dot(self.a2, self.W3) + self.b3
        self.a3 = softmax(self.z3) # Softmax
        return self.a3
        
    def fit(self, X, y_onehot, epochs=20, batch_size=16):
        loss_history = []
        n_samples = X.shape[0]
        
        for epoch in range(epochs):
            # Shuffle
            indices = np.random.permutation(n_samples)
            X_shuffled = X[indices]
            y_shuffled = y_onehot[indices]
            
            epoch_loss = 0.0
            num_batches = int(np.ceil(n_samples / batch_size))
            
            for b in range(num_batches):
                start_idx = b * batch_size
                end_idx = min(start_idx + batch_size, n_samples)
                xb = X_shuffled[start_idx:end_idx]
                yb = y_shuffled[start_idx:end_idx]
                
                # Forward
                pred = self.forward(xb)
                
                # Loss (Cross-Entropy)
                loss = -np.sum(yb * np.log(pred + 1e-15)) / len(xb)
                epoch_loss += loss * len(xb)
                
                # Backprop
                # dL/dz3 = pred - y
                dz3 = (pred - yb) / len(xb)
                dW3 = np.dot(self.a2.T, dz3)
                db3 = np.sum(dz3, axis=0, keepdims=True)
                
                # dL/da2 = dz3 * W3^T
                da2 = np.dot(dz3, self.W3.T)
                # dL/dz2 = da2 * (z2 > 0)
                dz2 = da2 * (self.z2 > 0)
                dW2 = np.dot(self.a1.T, dz2)
                db2 = np.sum(dz2, axis=0, keepdims=True)
                
                # dL/da1 = dz2 * W2^T
                da1 = np.dot(dz2, self.W2.T)
                # dL/dz1 = da1 * (z1 > 0)
                dz1 = da1 * (self.z1 > 0)
                dW1 = np.dot(xb.T, dz1)
                db1 = np.sum(dz1, axis=0, keepdims=True)
                
                # Update weights
                self.W3 -= self.lr * dW3
                self.b3 -= self.lr * db3
                self.W2 -= self.lr * dW2
                self.b2 -= self.lr * db2
                self.W1 -= self.lr * dW1
                self.b1 -= self.lr * db1
                
            loss_history.append(epoch_loss / n_samples)
            
        return loss_history

    def save_weights(self, filepath):
        """序列化儲存模型權重 (Industrial Backup)"""
        np.savez_compressed(filepath,
                            W1=self.W1, b1=self.b1,
                            W2=self.W2, b2=self.b2,
                            W3=self.W3, b3=self.b3)
        print(f"  [NumPyMLP] 模型權重已儲存至 {filepath}.npz")

    def load_weights(self, filepath):
        """載入已備份的模型權重 (Industrial Load)"""
        data = np.load(filepath)
        self.W1 = data['W1']; self.b1 = data['b1']
        self.W2 = data['W2']; self.b2 = data['b2']
        self.W3 = data['W3']; self.b3 = data['b3']
        print(f"  [NumPyMLP] 模型權重已從 {filepath} 載入完成")

class NumPyLSTMCell:
    """
    NumPy 實作之 LSTM 單元 (時序特徵提取)
    """
    def __init__(self, input_dim=4, hidden_dim=8):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # 門控權重與偏置 (併入一個大權重矩陣以利矩陣運算)
        # 門包含: f (forget), i (input), c (candidate), o (output)
        self.W = np.random.randn(input_dim + hidden_dim, 4 * hidden_dim) * np.sqrt(2.0 / (input_dim + hidden_dim))
        self.b = np.zeros((1, 4 * hidden_dim))
        
    def step(self, x, h_prev, c_prev):
        """
        單步前向傳播
        x: (batch_size, input_dim)
        h_prev: (batch_size, hidden_dim)
        c_prev: (batch_size, hidden_dim)
        """
        # 拼接輸入與隱藏狀態
        concat = np.hstack([h_prev, x]) # (batch_size, hidden_dim + input_dim)
        gates = np.dot(concat, self.W) + self.b # (batch_size, 4 * hidden_dim)
        
        # 分割門
        d = self.hidden_dim
        f_gate = sigmoid(gates[:, 0:d])
        i_gate = sigmoid(gates[:, d:2*d])
        c_tilde = np.tanh(gates[:, 2*d:3*d])
        o_gate = sigmoid(gates[:, 3*d:4*d])
        
        # 更新細胞狀態與隱藏狀態
        c_next = f_gate * c_prev + i_gate * c_tilde
        h_next = o_gate * np.tanh(c_next)
        
        return h_next, c_next

    def forward_sequence(self, X_seq):
        """
        序列前向傳播
        X_seq: (batch_size, seq_len, input_dim)
        """
        batch_size, seq_len, _ = X_seq.shape
        h = np.zeros((batch_size, self.hidden_dim))
        c = np.zeros((batch_size, self.hidden_dim))
        
        for t in range(seq_len):
            xt = X_seq[:, t, :]
            h, c = self.step(xt, h, c)
            
        return h # 回傳最後一個時間步的隱藏狀態

class NumPyBiGRUWithAttention:
    """
    NumPy 實作之雙向 GRU + 自注意力機制 (Bi-GRU + Attention)
    """
    def __init__(self, input_dim=4, hidden_dim=8, output_dim=12):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # 正向 GRU 權重 (r: reset, z: update, h: candidate)
        self.W_f = np.random.randn(input_dim + hidden_dim, 3 * hidden_dim) * np.sqrt(2.0 / (input_dim + hidden_dim))
        self.b_f = np.zeros((1, 3 * hidden_dim))
        
        # 反向 GRU 權重
        self.W_b = np.random.randn(input_dim + hidden_dim, 3 * hidden_dim) * np.sqrt(2.0 / (input_dim + hidden_dim))
        self.b_b = np.zeros((1, 3 * hidden_dim))
        
        # Attention 權重
        self.W_a = np.random.randn(2 * hidden_dim, 1) * np.sqrt(2.0 / (2 * hidden_dim))
        self.b_a = np.zeros((1, 1))
        
        # 分類輸出 dense 權重
        self.W_out = np.random.randn(2 * hidden_dim, output_dim) * np.sqrt(2.0 / (2 * hidden_dim))
        self.b_out = np.zeros((1, output_dim))

    def _gru_step(self, x, h_prev, W, b):
        concat = np.hstack([h_prev, x])
        gates = np.dot(concat, W) + b
        
        d = self.hidden_dim
        r = sigmoid(gates[:, 0:d])
        z = sigmoid(gates[:, d:2*d])
        
        # 候選隱藏狀態
        concat_cand = np.hstack([r * h_prev, x])
        # 我們將 candidate 權充分出來計算
        # 為了簡化，直接用 gates[:, 2*d:3*d] 當候選狀態計算 (或做縮排)
        h_tilde = np.tanh(np.dot(concat_cand, W[:, 2*d:3*d]) + b[:, 2*d:3*d])
        
        h_next = (1.0 - z) * h_prev + z * h_tilde
        return h_next

    def forward(self, X_seq):
        """
        X_seq: (batch_size, seq_len, input_dim)
        """
        batch_size, seq_len, _ = X_seq.shape
        
        # 1. 正向 GRU
        h_f = np.zeros((batch_size, self.hidden_dim))
        h_forward_history = []
        for t in range(seq_len):
            h_f = self._gru_step(X_seq[:, t, :], h_f, self.W_f, self.b_f)
            h_forward_history.append(h_f)
            
        # 2. 反向 GRU
        h_b = np.zeros((batch_size, self.hidden_dim))
        h_backward_history = [None] * seq_len
        for t in reversed(range(seq_len)):
            h_b = self._gru_step(X_seq[:, t, :], h_b, self.W_b, self.b_b)
            h_backward_history[t] = h_b
            
        # 3. 拼接正反向 hidden 狀態 H_t
        H = [] # 列表長度為 seq_len, 元素為 (batch_size, 2 * hidden_dim)
        for t in range(seq_len):
            H_t = np.hstack([h_forward_history[t], h_backward_history[t]])
            H.append(H_t)
            
        H = np.stack(H, axis=1) # (batch_size, seq_len, 2 * hidden_dim)
        
        # 4. Attention 機制
        # score = tanh(H * W_a + b_a)
        # 這裡為了簡化，直接將三維 H 與 2D W_a 做點積
        H_flat = H.reshape(-1, 2 * self.hidden_dim) # (batch_size * seq_len, 2*hidden_dim)
        scores_flat = np.dot(H_flat, self.W_a) + self.b_a # (batch_size * seq_len, 1)
        scores = scores_flat.reshape(batch_size, seq_len) # (batch_size, seq_len)
        
        # Softmax 計算 attention 權重
        alpha = softmax(scores) # (batch_size, seq_len)
        self.alpha_viz = alpha # 用於視覺化分析之權重暫存
        
        # Context vector c = sum(alpha_t * H_t)
        context = np.sum(alpha[:, :, np.newaxis] * H, axis=1) # (batch_size, 2 * hidden_dim)
        
        # 5. Output Dense
        out = np.dot(context, self.W_out) + self.b_out
        return softmax(out)

class AutogradTensor:
    """
    實施改善計畫：自研輕量級自動微分引擎 (Autograd Engine)
    支援動態計算圖與自動反向傳播
    """
    def __init__(self, data, creators=None, op=None):
        self.data = np.array(data, dtype=np.float32)
        self.creators = creators or []
        self.op = op
        self.grad = None
        self.children = {}
        for c in self.creators:
            c.children[id(self)] = self

    def backward(self, grad=None):
        if grad is None:
            grad = np.ones_like(self.data)
        if self.grad is None:
            self.grad = grad
        else:
            self.grad += grad

        if self.op == "add":
            self.creators[0].backward(self.grad)
            self.creators[1].backward(self.grad)
        elif self.op == "matmul":
            X, W = self.creators[0], self.creators[1]
            X.backward(np.dot(self.grad, W.data.T))
            W.backward(np.dot(X.data.T, self.grad))
        elif self.op == "relu":
            X = self.creators[0]
            X.backward(self.grad * (X.data > 0))
        elif self.op == "sigmoid":
            X = self.creators[0]
            s = 1.0 / (1.0 + np.exp(-np.clip(X.data, -500, 500)))
            X.backward(self.grad * s * (1.0 - s))

    def __add__(self, other):
        return AutogradTensor(self.data + other.data, creators=[self, other], op="add")

    def matmul(self, other):
        return AutogradTensor(np.dot(self.data, other.data), creators=[self, other], op="matmul")

    def relu(self):
        return AutogradTensor(np.maximum(0, self.data), creators=[self], op="relu")

class AutogradMLP:
    """
    利用自研 AutogradTensor 進行前向與反向自動求解的輕量 MLP 分類器
    """
    def __init__(self, input_dim=4, hidden=32, output_dim=12, lr=0.01):
        self.lr = lr
        self.W1 = AutogradTensor(np.random.randn(input_dim, hidden) * np.sqrt(2.0 / input_dim))
        self.b1 = AutogradTensor(np.zeros((1, hidden)))
        self.W2 = AutogradTensor(np.random.randn(hidden, output_dim) * np.sqrt(2.0 / hidden))
        self.b2 = AutogradTensor(np.zeros((1, output_dim)))

    def forward(self, X):
        self.X_tensor = AutogradTensor(X)
        self.h1 = self.X_tensor.matmul(self.W1) + self.b1
        self.a1 = self.h1.relu()
        self.out = self.a1.matmul(self.W2) + self.b2
        return softmax(self.out.data)

    def step(self, X, y_onehot):
        probs = self.forward(X)
        loss = -np.sum(y_onehot * np.log(probs + 1e-15)) / len(X)
        
        for param in [self.W1, self.b1, self.W2, self.b2]:
            param.grad = None
            
        grad_out = (probs - y_onehot) / len(X)
        self.out.backward(grad_out)
        
        self.W1.data -= self.lr * self.W1.grad
        self.b1.data -= self.lr * np.sum(self.b1.grad, axis=0, keepdims=True)
        self.W2.data -= self.lr * self.W2.grad
        self.b2.data -= self.lr * np.sum(self.b2.grad, axis=0, keepdims=True)
        
        return loss

    def save_weights(self, filepath):
        """序列化儲存 AutogradMLP 模型權重"""
        np.savez_compressed(filepath,
                            W1=self.W1.data, b1=self.b1.data,
                            W2=self.W2.data, b2=self.b2.data)
        print(f"  [AutogradMLP] 模型權重已儲存至 {filepath}.npz")

    def load_weights(self, filepath):
        """載入 AutogradMLP 模型權重"""
        data = np.load(filepath)
        self.W1 = AutogradTensor(data['W1'])
        self.b1 = AutogradTensor(data['b1'])
        self.W2 = AutogradTensor(data['W2'])
        self.b2 = AutogradTensor(data['b2'])
        print(f"  [AutogradMLP] 模型權重已從 {filepath} 載入完成")

