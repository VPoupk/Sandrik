"""Pure-Python Keccak-256 (Ethereum) — no deps."""
_RC=[0x0000000000000001,0x0000000000008082,0x800000000000808A,0x8000000080008000,
0x000000000000808B,0x0000000080000001,0x8000000080008081,0x8000000000008009,
0x000000000000008A,0x0000000000000088,0x0000000080008009,0x000000008000000A,
0x000000008000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,
0x8000000000008002,0x8000000000000080,0x000000000000800A,0x800000008000000A,
0x8000000080008081,0x8000000000008080,0x0000000080000001,0x8000000080008008]
_ROT=[[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],[28,55,25,21,56],[27,20,39,8,14]]
def _rol(x,n): return ((x<<n)|(x>>(64-n)))&0xFFFFFFFFFFFFFFFF
def _keccak_f(S):
    for rc in _RC:
        C=[S[x][0]^S[x][1]^S[x][2]^S[x][3]^S[x][4] for x in range(5)]
        D=[C[(x-1)%5]^_rol(C[(x+1)%5],1) for x in range(5)]
        for x in range(5):
            for y in range(5): S[x][y]^=D[x]
        B=[[0]*5 for _ in range(5)]
        for x in range(5):
            for y in range(5): B[y][(2*x+3*y)%5]=_rol(S[x][y],_ROT[x][y])
        for x in range(5):
            for y in range(5): S[x][y]=B[x][y]^((~B[(x+1)%5][y])&B[(x+2)%5][y])
        S[0][0]^=rc
    return S
def keccak256(data: bytes) -> bytes:
    rate=136
    S=[[0]*5 for _ in range(5)]
    pad=data+b'\x01'+b'\x00'*((rate-(len(data)+1)%rate)%rate)
    pad=bytearray(pad); pad[-1]^=0x80
    for off in range(0,len(pad),rate):
        blk=pad[off:off+rate]
        for i in range(rate//8):
            w=int.from_bytes(blk[i*8:i*8+8],'little')
            S[i%5][i//5]^=w
        S=_keccak_f(S)
    out=b''
    for i in range(4):
        out+=int(S[i%5][i//5]).to_bytes(8,'little')
    return out[:32]
def topic(sig: str) -> str:
    return "0x"+keccak256(sig.encode()).hex()
if __name__=="__main__":
    # sanity: keccak256("") = c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
    assert keccak256(b"").hex()=="c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    # Transfer(address,address,uint256)
    assert topic("Transfer(address,address,uint256)")=="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    # V3 Swap
    assert topic("Swap(address,address,int256,int256,uint160,uint128,int24)")=="0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    print("keccak OK")
    print("V4 Swap:", topic("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)"))
    print("V4 ModifyLiquidity:", topic("ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)"))
