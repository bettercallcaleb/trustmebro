import os
import tempfile
from pathlib import Path

from . import alternatives, numeric


def fd_offset(r):
    alphabet="abcdefghijklmnopqrstuvwxyz"
    k=r.randrange(0,26)
    content=(alphabet[k:]+alphabet[:k]).encode()
    def execute(level):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bytes"
            path.write_bytes(content)
            a=os.open(path,os.O_RDONLY)
            b=None
            try:
                if level==1:
                    os.read(a,3)
                    return os.read(a,2).decode()
                if level==2:
                    b=os.dup(a)
                    os.read(a,3)
                    return os.read(b,2).decode()
                if level==3:
                    b=os.open(path,os.O_RDONLY)
                    os.read(a,3)
                    return os.read(b,2).decode()
                b=os.dup(a)
                os.read(a,3)
                os.lseek(b,2,os.SEEK_CUR)
                return os.read(a,2).decode()
            finally:
                if b is not None:os.close(b)
                os.close(a)
    data=content.decode()
    prompts=[
        f"POSIX file contains ASCII bytes '{data}'. fd=open(file,O_RDONLY); read(fd,3); answer=read(fd,2). What exact two ASCII characters are in answer?",
        f"POSIX file contains ASCII bytes '{data}'. fd1=open(file,O_RDONLY); fd2=dup(fd1); read(fd1,3); answer=read(fd2,2). What exact two ASCII characters are in answer?",
        f"POSIX file contains ASCII bytes '{data}'. fd1=open(file,O_RDONLY); fd2=open(file,O_RDONLY) INDEPENDENTLY; read(fd1,3); answer=read(fd2,2). What exact two ASCII characters are in answer?",
        f"POSIX file contains ASCII bytes '{data}'. fd1=open(file,O_RDONLY); fd2=dup(fd1); read(fd1,3); lseek(fd2,2,SEEK_CUR); answer=read(fd1,2). What exact two ASCII characters are in answer?",
    ]
    out=[]
    for level,prompt in enumerate(prompts,1):
        answer=execute(level)
        distract=[data[i:i+2] for i in range(0,12)]
        r.shuffle(distract)
        out.append((prompt,*alternatives(answer,distract)))
    return ("sys-hard","posix-file-offsets","https://man7.org/linux/man-pages/man2/dup.2.html",out)


def modes(r):
    mask=r.choice([0o027,0o022,0o077,0o037,0o047,0o007,0o026,0o057])
    user=r.randrange(4,8)
    group=r.randrange(0,7)
    other=r.randrange(0,7)
    initial=(user<<6)|(group<<3)|other
    def octal(value):
        return f"0{value:03o}"
    def distractors(value):
        wrong=[value^0o020, value^0o004, value^0o002, value^0o001, value^0o040, value^0o100]
        return alternatives(octal(value),[octal(x&0o777) for x in wrong])
    v1=0o666 & ~mask
    v2=0o777 & ~mask
    v3=(initial&~0o070)|(((initial>>6)&0o7)<<3)
    created=0o666 & ~mask
    group_from_user=(created&~0o070)|(((created>>6)&7)<<3)
    other_from_group=(group_from_user&~0o007)|(((group_from_user>>3)&7))
    v4=other_from_group&~0o200
    prompts=[
        f"POSIX mkdir/open mode arithmetic. A process calls open(path,O_CREAT,0666) on a NEW regular file, with umask {octal(mask)}. Ignore default ACLs. What permission bits result? Reply with 4-character octal including leading zero.",
        f"POSIX mode arithmetic. mkdir(path,0777) on a NEW directory with umask {octal(mask)}. Ignore default ACLs. What permission bits result? Reply with 4-character octal including leading zero.",
        f"A POSIX file currently has mode {octal(initial)}. chmod g=u copies the CURRENT owner's rwx bits to the group bits, without changing other classes. What is the resulting 4-character octal mode?",
        f"On a POSIX regular file newly created with requested mode 0666 and umask {octal(mask)}, execute in order: chmod g=u; chmod o=g; chmod u-w. Ignore ACLs and special bits. What is the final 4-character octal mode?",
    ]
    out=[]
    for p,a in zip(prompts,[v1,v2,v3,v4]):
        out.append((p,*distractors(a)))
    return ("sys-hard","unix-mode-bit-transforms","https://man7.org/linux/man-pages/man2/umask.2.html",out)


def endian(r):
    octets=bytes(r.sample(range(16,240),4))
    b=' '.join(f"{v:02X}" for v in octets)
    le=int.from_bytes(octets,"little")
    be=int.from_bytes(octets,"big")
    sign=int.from_bytes(octets[:2],"little",signed=True)
    vals=[
        le&0xffff,
        (be>>16)&0xffff,
        (sign>>3)&0xffff,
        ((le>>5) ^ (le>>11)) & 0xffff,
    ]
    prompts=[
        f"Four memory bytes at increasing addresses are {b}. Treat the first TWO bytes as an unsigned little-endian 16-bit integer. What is its 4-digit uppercase hex value (no 0x)?",
        f"Four memory bytes at increasing addresses are {b}. Treat all FOUR as a big-endian unsigned 32-bit integer. What is its HIGH 16-bit half, as 4 uppercase hex digits (no 0x)?",
        f"Four memory bytes are {b}. Read the FIRST TWO as a signed two's-complement little-endian 16-bit integer. Apply arithmetic right-shift by 3, then mask with 0xFFFF. Output 4 uppercase hex digits (no 0x).",
        f"Four memory bytes are {b}, forming unsigned 32-bit little-endian X. Compute ((X >> 5) XOR (X >> 11)) AND 0xFFFF. Answer using exactly 4 uppercase hex digits (no 0x).",
    ]
    out=[]
    for prompt,val in zip(prompts,vals):
        answer=f"{val:04X}"
        wrong=[f"{(val^mask)&0xffff:04X}" for mask in (0x0100,0x0010,0x0001,0x1000,0x0040)]
        out.append((prompt,*alternatives(answer,wrong)))
    return ("sys-hard","endian-signed-bitfields","https://www.kernel.org/doc/html/latest/core-api/unaligned-memory-access.html",out)


BUILDERS=[fd_offset,modes,endian]
