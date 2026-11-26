import json
import re

LABEL=r"(?:final(?: answer| result| cumulative ack| ack| list| output| selection| permission| node eligibility| count)?|answer|result|solution|corrected answer|output|return(?: the value| only the integer)?|end of answer|inal)"
FENCE=re.compile(r"(?ms)^[ \t]*\x60{3}(?:[A-Za-z0-9_-]+)?[ \t]*\n(.*?)\n[ \t]*\x60{3}[ \t]*(?=\n|\Z)")
INT=r"[+-]?[0-9]{1,30}"
NEGATIVE=re.compile(r"(?i)\b(?:cannot (?:choose|decide|determine|provide|answer)|not (?:my|the) (?:final )?answer|not endors(?:ed|ing)|remain(?:s)? (?:uncertain|possible)|not yet (?:verified|decided)|withdraw|retract|no committed answer|no answer has been established|not sure|undecided|unverified)\b")
ABSTAIN=re.compile(r"(?i)^(?:unknown|no (?:completed,? )?(?:unambiguous |committed |definitive |final )?answer (?:exists|is (?:provided|established|available)|has been (?:provided|established))|(?:there is|the author (?:provides|provided|has provided)) no (?:completed |committed |unambiguous |definitive |final )?answer)[.!]?$")
CONCLUSION=re.compile(r"(?i)^(?:(?:so|therefore|thus|hence|accordingly)[,]?\s+)?(?:the\s+)?(?:correct (?:and only )?answer|(?:final|correct|requested|extracted|committed|verified) (?:answer|result|value|integer|number|interface|count|permission|permission bits)|answer|result|remainder|output|minimum total cost|selected interface|interface selected|integer (?:returned|[AB] reads)|first positive minute (?:when|at which) both machines run together|final (?:cumulative )?ack(?: number)?|ack number sent after the last segment|number of outgoing (?:IPv4 )?fragments|number of usable host addresses|remaining TTL|resulting permission bits(?: for the directory)?)\s+(?:is|are|equals|would be|will be)\s*:?\s*(.*)$")
HEAD=re.compile(r"(?i)^"+LABEL+r"(?:\s+is)?\s*:?\s*$")
FORMAT_PATTERNS={
 "integer":[r"(?:the )?(?:connection )?[AB] (?:reads|sees|will read|will see) (?:the (?:updated |original |current )?value(?: of)? )?(.+?)(?: after the commit.*| as .*)?",r"(?:the )?integer (?:that )?[AB] reads is (.+)",r"(?:the )?number of (?:accepted tokens|authorized requests|fragments|expired records) is (.+)",r"(?:only )?("+INT+r") (?:tokens|requests|nodes|records) (?:are )?(?:accepted|authorized|eligible|expired)",r"all ("+INT+r") (?:tokens|requests|nodes|records) are (?:accepted|authorized|eligible|expired)",r"(?:.*? — )?total of ("+INT+r") values",r"("+INT+r") fragments",r"(?:the )?minimum total cost is (.+)",r"(?:the )?first positive minute.*? is ("+INT+r")(?: minutes)?",r"(?:the )?query returns (.+)",r"(?:the )?result(?: for id = [0-9]+)? is (.+)"],
 "interface":[r"(?:the )?(?:requested|selected|correct) interface is (.+)",r"interface (if[0-9]+)",r"(.+?) is selected(?: as the (?:interface|route))?",r"(?:the )?final answer is the interface (.+)",r"(?:the )?interface with (?:the )?.+? is (if[0-9]+)"],
 "hex4":[r"(?:the )?(?:hexadecimal (?:value|representation)|4-digit (?:uppercase )?hex(?:adecimal)? (?:value|result)) is (.+)",r".+?, which as a hex number is (.+)"],
 "octal":[r"(?:the )?(?:final|resulting|requested) (?:permission(?: bits)?|octal (?:value|result)) (?:is|are) (.+)"],
 "bitstring":[r"(?:the )?(?:requested|final|resulting) (?:bitstring|bit string|binary(?: representation| value)|bit sequence|output) is (.+)"],
 "text2":[r"(?:the )?(?:two|2|first two) (?:ASCII )?(?:characters|bytes)(?: (?:that are )?read(?: from .+?)?)?(?: in the (?:answer|final read|requested value|))?\s+(?:are|is)\s*:?\s*(.+)",r"(?:the )?two[- ]character string(?: in the(?: answer)?)?\s+is\s*:?\s*(.+)",r"(?:the )?two ASCII characters in the are\s+(.+)"],
 "csv":[r"(?:the )?(?:sorted list|sorted (?:numbers|sequence)|comma-separated (?:list|values)|resulting sequence)(?: is| are)?\s*:\s*(.+)"],
 "csv_none":[r"(?:the )?(?:filtered list|filtered (?:numbers|sequence)|comma-separated (?:list|values)|remaining numbers)(?: is| are)?\s*:\s*(.+)"],
}

def strip_markdown(s):
    s=s.strip()
    s=re.sub(r"^\s*(?:(?:>\s*|#{1,6}\s+|[-*]\s+|✅\s*))+","",s)
    s=re.sub(r"\*\*([^*\n]+)\*\*",r"\1",s)
    s=re.sub(r"__([^_\n]+)__",r"\1",s)
    return s.strip()

def payload(spec,s):
    import recovery as r
    z=strip_markdown(s)
    z=r.unwrap(z)
    z=re.sub(r"^✅\s*|\s*✅$","",z).strip()
    if z.endswith(".") and not z.endswith("..."):z=r.unwrap(z[:-1].rstrip())
    z=z.strip()
    fmt=spec.get("format")
    if spec.get("kind")=="delivery" and spec.get("contract")!="json":fmt="integer"
    if fmt=="integer" and re.fullmatch(r"[+-]?[0-9]{1,30}\.[0-9]{1,30}",z):
        return z,"noninteger_decimal_claim"
    if fmt=="identifier" and re.fullmatch(r"[A-Za-z0-9]+-[0-9]+",z):
        return z,"identifier_missing_prefix"
    if fmt=="text2":
        quoted=re.fullmatch(r"(['\"])([ -~])\1\s+(?:and\s+)?(['\"])([ -~])\3",z)
        if quoted:return quoted[2]+quoted[4],"quoted_character_pair"
        pair=re.fullmatch(r"(?i)[\x60'\"]?([a-z0-9])[\x60'\"]?\s*(?:,|and|\s)\s*[\x60'\"]?([a-z0-9])[\x60'\"]?",z)
        if pair:return pair[1]+pair[2],"character_pair"
    if fmt in ("integer","hex4","octal","error_code") and re.fullmatch(r"\([+-]?[0-9]+\)",z):
        z=z[1:-1]
    if fmt in ("integer","bitstring","hex4","octal","error_code","csv","csv_none","interface","text2","identifier"):
        if len(z)>1 and z[0]==z[-1] and z[0] in "\"'":
            z=z[1:-1]
        if fmt in ("csv","csv_none","bitstring"):
            if z.startswith("[") and z.endswith("]"):
                try:
                    v=json.loads(z)
                    if isinstance(v,list) and all(type(x) is int for x in v):
                        if fmt=="csv_none" and not v:return "NONE","empty_list_representation"
                        if fmt=="bitstring" and all(x in (0,1) for x in v):return "".join(map(str,v)),"bit_array"
                        if fmt!="bitstring" and v:return ",".join(map(str,v)),"csv_array"
                except ValueError:pass
        if fmt=="bitstring":
            m=re.fullmatch(r"\{\s*([01](?:\s*,\s*[01])*)\s*\}",z)
            if m:return re.sub(r"[,\s]","",m[1]),"braced_bit_array"
            if re.fullmatch(r"(?i)(?:eligible|ineligible|authorized|unauthorized|denied|accepted|rejected|expired|not expired)(?:\s*,\s*(?:eligible|ineligible|authorized|unauthorized|denied|accepted|rejected|expired|not expired))*",z):
                positives={"eligible","authorized","accepted","expired"}
                return "".join("1" if x.strip().lower() in positives else "0" for x in z.split(",")),"explicit_status_sequence"
            try:
                obj=json.loads(z)
                if isinstance(obj,dict) and obj and all(re.fullmatch(r"n[1-9][0-9]*",k) for k in obj) and all(type(v) is int and v in (0,1) for v in obj.values()):
                    if sorted(int(k[1:]) for k in obj)==list(range(1,len(obj)+1)):return "".join(str(obj[f"n{i}"]) for i in range(1,len(obj)+1)),"numbered_node_map"
            except ValueError:pass
            if re.fullmatch(r"\[[01]\]\s+[01]",z):
                b=re.findall(r"[01]",z)
                if b[0]==b[1]:return b[0],"repeated_single_bit"
            if re.fullmatch(r"[01](?:[,\s]+[01])+",z):return re.sub(r"[,\s]","",z),"bit_delimiters"
        if fmt=="hex4" and re.fullmatch(r"\(\s*[0-9A-Fa-f](?:\s*,\s*[0-9A-Fa-f])+\s*\)",z):
            return re.sub(r"[^0-9A-Fa-f]","",z).upper(),"hex_digit_tuple"
        if fmt=="hex4" and re.fullmatch(r"[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})+",z):
            return re.sub(r"\s+","",z).upper(),"hex_byte_sequence"
        if fmt=="text2":
            m=re.fullmatch(r"(?i)['\"]([a-z])['\"]\s*(?:,|and)\s*['\"]([a-z])['\"]",z)
            if m:return m[1]+m[2],"character_pair"
        if fmt=="interface":
            if re.fullmatch(r"[0-9]{1,2}",z):return "if"+z.zfill(2),"interface_number"
            m=re.fullmatch(r"(?i)(?:interface\s+)?(if[0-9]+|eth(?:if)?[0-9]+)",z)
            if m:return m[1].lower(),"interface_name"
            m=re.fullmatch(r"(?i)(?:interface\s+)([0-9]{1,2})",z)
            if m:return "if"+m[1].zfill(2),"interface_number"
            try:
                obj=json.loads(z)
                if isinstance(obj,dict) and set(obj)=={"selected_interface"} and isinstance(obj["selected_interface"],str):return payload(spec,obj["selected_interface"])
            except ValueError:pass
            m=re.fullmatch(r"(?i)\(?[0-9.]+/[0-9]+\s*,\s*(?:interface\s+)?[0-9]+\s*,\s*(if[0-9]+)\)?",z)
            if m:return m[1].lower(),"route_tuple_interface"
            m=re.fullmatch(r"(?i)(if[0-9]+)\s*\([0-9.]+/[0-9]+,\s*metric\s+[0-9]+\)",z)
            if m:return m[1].lower(),"interface_with_route_metadata"
            m=re.fullmatch(r"(?i)[0-9.]+/[0-9]+\s+(?:via|with metric [0-9]+ on)\s+interface\s+((?:if)?[0-9]+)",z)
            if m:return payload(spec,m[1])
        if fmt=="integer":
            m=re.fullmatch(r"(?i)[0-9.+*/^− ()-]+\s*[=≡]\s*("+INT+r")\s*\(mod\s+[0-9]+\)",z)
            if m and spec.get("family")=="modular":return str(int(m[1])),"explicit_modular_equation"
        if fmt=="octal" and re.fullmatch(r"[0-9a-fA-F]+",z) and re.search(r"[89a-fA-F]",z):
            return z,"invalid_octal_digits"
        if fmt=="integer" and z.lower() in ("none","null","(null)"):
            if spec.get("family") in ("jwt-boundary-validation","kubernetes-rbac-scope") and z.lower()=="none":return "0","explicit_zero_count"
            return z,"noninteger_null_claim"
        if fmt=="integer" and re.fullmatch(r"[0-9.]+/[0-9]+",z):
            return z,"wrong_entity_cidr"
        if fmt=="identifier" and re.fullmatch(r"ID-[A-Za-z0-9-]+",z,re.I):
            return z,"identifier_wrong_shape"
        if fmt=="integer":
            if spec.get("family")=="tcp-send-window":
                m=re.fullmatch(r"[0-9B +*/()−-]+\s*=\s*("+INT+r")\s*(?:B|bytes?)",z,re.I)
                if m:return str(int(m[1])),"explicit_byte_equation_rhs"
            units={"schedule":r"minutes?","dns-ttl-chain":r"seconds?","tcp-send-window":r"(?:additional new payload )?bytes?|B","ipv4-fragment-offset":r"fragments?","ipv4-cidr-boundaries":r"hosts?|usable host addresses","jwt-boundary-validation":r"tokens?","kubernetes-rbac-scope":r"(?:authorized )?requests?"}
            u=units.get(spec.get("family"))
            if u and re.fullmatch(INT+r"\s*(?:"+u+r")",z,re.I):
                return str(int(re.match(INT,z)[0])),"unit_suffix"
        if fmt=="csv_none" and z.casefold() in ("none","no matches","no matching values","empty"):return "NONE","explicit_empty_sequence"
    return r.parse_value(spec,z,True)

def key(spec,v):
    import recovery as r
    fmt=spec.get("format")
    if fmt in ("hex4","octal","error_code","interface"):
        from conceptladder.exact import normalize_exact
        try:
            q=normalize_exact(v,fmt)
            if q is not None:return r.canonical(q)
        except (TypeError,ValueError):pass
    return r.canonical(v)

def finish_result(spec,claims,method,steps=()):
    import recovery as r
    if not claims:return r.result(r.MISSING,"no_extracted_claim",steps)
    keys={key(spec,v) for v,_,_ in claims}
    if len(keys)!=1:
        d=r.result(r.MISSING,"conflicting_declarations",steps)
        d["claim_evidence"]=[{"candidate":v,"text":e[:350],"rule":m} for v,e,m in claims[:8]]
        return d
    v,e,m=claims[-1]
    d=r.result(v,method,[*steps,m])
    d["claim_evidence"]=[{"candidate":v,"text":e[:350],"rule":m} for v,e,m in claims[:8]]
    return d

def clean_visible(s):
    import recovery as r
    for _ in range(7):
        old=s
        s=r.ROLE.sub("",s.strip(),count=1).strip()
        s=re.sub(r"^(?:</think>\s*)+","",s,flags=re.I).strip()
        s=re.sub(r"(?is)^<think>.*?</think>\s*","",s,count=1).strip()
        if s==old:break
    if r.BLOCKED.search(s):return None
    if re.search(r"</?think>",s,re.I):
        if re.search(r"<think>",s,re.I) and not re.search(r"</think>",s,re.I):
            return None
        s=re.sub(r"</think>","",s,flags=re.I)
        if re.search(r"<think>",s,re.I):return None
    return s.strip()

def loose_json(s):
    import recovery as r
    s=s.strip()
    if s.startswith("$$"):
        s=s[2:].strip()
        if s.endswith("$$"):s=s[:-2].strip()
    if s.startswith(r"\{") and s.endswith(r"\}"):s="{"+s[2:-2]+"}"
    v,m=r.json_parse(s)
    if v is not r.MISSING or m=="conflicting_json_keys":return v,m
    if s.startswith("{") and s.endswith("}"):
        pieces=re.split(r'("(?:\\.|[^"\\])*")',s)
        for i in range(0,len(pieces),2):
            pieces[i]=re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)",r'\1"\2"\3',pieces[i])
        z="".join(pieces)
        if z!=s:
            v,m=r.json_parse(z)
            if v is not r.MISSING:return v,"unquoted_json_keys"
    return v,m

def json_blocks(s):
    import recovery as r
    blocks=[]
    for f in FENCE.finditer(s):
        body=f[1].strip()
        if body.startswith(("{","[",r"\{")):blocks.append((f.start(),f.end(),body))
    for m in re.finditer(r"(?m)^[ \t]*(?:(?:FINAL|ANSWER|OUTPUT|RESULT)\s*:\s*)?(?=[{\[])",s,re.I):
        start=m.end()
        if any(a<=start<b for a,b,_ in blocks):continue
        z=s[start:]
        depth=[];quoted=False;escape=False;end=None
        for i,ch in enumerate(z):
            if quoted:
                if escape:escape=False
                elif ch=="\\":escape=True
                elif ch=='"':quoted=False
            elif ch=='"':quoted=True
            elif ch in "{[":depth.append(ch)
            elif ch in "}]":
                if not depth or depth[-1]!={"}":"{","]":"["}[ch]:break
                depth.pop()
                if not depth:end=i+1;break
        if end is not None:
            blocks.append((start,start+end,z[:end]))
    return sorted(blocks)

def structured(spec,s):
    import recovery as r
    is_extract=spec.get("kind")=="extraction"
    is_delivery=spec.get("contract")=="json"
    claims=[];conflict=False
    def add(obj,e,m):
        nonlocal conflict
        if is_extract:
            if isinstance(obj,dict) and "answer" in obj:
                a=obj["answer"];q=obj.get("quote")
                if isinstance(a,str) and a.strip().upper()=="UNKNOWN":
                    if set(obj)<={"answer","quote"}:claims.append(({"decision":"abstain"},e,m))
                else:
                    a=r.int_value(a)
                    if a is not r.MISSING:claims.append(({"decision":"extract","answer":a,"quote":q},e,m))
            elif isinstance(obj,(str,int)) and type(obj) is not bool:
                a=r.int_value(obj)
                if a is not r.MISSING:claims.append(({"decision":"extract","answer":a,"quote":None},e,m))
        elif is_delivery:
            if isinstance(obj,dict):
                a=r.int_value(obj.get("answer"))
                if a is not r.MISSING:claims.append((a,e,m))
        else:
            if isinstance(obj,dict) and spec.get("kind")!="protocol" and type(obj.get("count")) is str and r.INTEGER.fullmatch(obj["count"]):
                obj={**obj,"count":int(obj["count"])}
            claims.append((obj,e,m))
    obj,m=loose_json(s)
    if m=="conflicting_json_keys":return r.result(r.MISSING,m)
    if obj is not r.MISSING:
        add(obj,s,m)
    else:
        blocks=json_blocks(s)
        for a,b,body in blocks:
            pre=s[:a].rstrip().splitlines()
            if pre and re.search(r"(?i)\b(?:example|hypothetical|schema|template)\s*:?\s*$",pre[-1]):continue
            value,m=loose_json(body)
            if m=="conflicting_json_keys":conflict=True
            elif value is not r.MISSING:add(value,body,m)
        if conflict:return r.result(r.MISSING,"conflicting_json_keys")
    if is_extract:
        z=strip_markdown(s)
        z=re.sub(r"\*\*([^*\n]+)\*\*",r"\1",z)
        pair=re.fullmatch(r"(?is)\s*answer\s*:?\s*\n?\s*([+-]?[0-9]+|UNKNOWN)\s*[.]?\s*(?:\n+\s*quote\s*:?\s*(.*))?",z)
        if pair:
            q=pair[2].strip() if pair[2] else None
            if q and q.startswith('"') and q.endswith('"'):q=q[1:-1]
            add({"answer":pair[1],"quote":q},z,"answer_quote_fields")
        tags=re.fullmatch(r"(?is)\s*(?:<answer>\s*(.*?)\s*</answer>\s*)?(?:<quote>\s*(.*?)\s*</quote>\s*)?>?\s*(?:<answer>\s*(.*?)\s*</answer>\s*)?>?\s*",s)
        if tags and (tags[1] is not None or tags[3] is not None):
            a=(tags[1] if tags[1] is not None else tags[3]).strip()
            if tags[1] is not None and tags[3] is not None:return r.result(r.MISSING,"conflicting_declarations")
            a=a.strip('"')
            q=tags[2]
            if q and q.startswith('"') and q.endswith('"'):q=q[1:-1]
            add({"answer":a,"quote":q},s,"xml_answer_quote_fields")
        if not claims:
            lines=[strip_markdown(l) for l in s.splitlines() if l.strip()]
            if lines:
                last=lines[-1]
                if ABSTAIN.fullmatch(last):
                    claims.append(({"decision":"abstain"},last,"explicit_abstention_phrase"))
                elif len(lines)>1 and re.search(r"(?i)(?:^|[.!?]\s+)(?:therefore,\s*)?(?:the\s+)?(?:extracted integer|answer|extracted answer|final answer|correct response)\s*(?:is)?\s*:\s*$",lines[-2]):
                    a=r.int_value(last)
                    if a is not r.MISSING:claims.append(({"decision":"extract","answer":a,"quote":None},last,"split_extracted_answer"))
        if not claims:
            explicit_numbers=re.findall(r"(?im)^\s*(?:return exactly:|final answer(?: is|:))\s*\"?("+INT+r")\.?\"?\s*$",s)
            if len(set(explicit_numbers))>1:
                return r.result(r.MISSING,"conflicting_declarations")
            m=re.fullmatch(r"\(("+INT+r")\)",s)
            if m:claims.append(({"decision":"extract","answer":str(int(m[1])),"quote":None},s,"parenthesized_extraction"))
            elif lines:
                last=lines[-1]
                for pat in (r"(?i)(?:my|the) (?:corrected |extracted |final )?answer is (?:exactly )?("+INT+r")\.",r"(?i)return exactly:\s*("+INT+r")\.?"):
                    m=re.fullmatch(pat,last)
                    if m:claims.append(({"decision":"extract","answer":str(int(m[1])),"quote":None},last,"explicit_extraction_conclusion"));break
        if claims:
            semantic_keys={(c.get("decision"),c.get("answer")) for c,_,_ in claims}
            if len(semantic_keys)>1:return finish_result(spec,claims,"structured_claim")
            if all(c.get("decision")=="extract" for c,_,_ in claims):
                quotes={r.canonical(c.get("quote")) for c,_,_ in claims if c.get("quote") is not None}
                if len(quotes)>1:return r.result(r.MISSING,"conflicting_evidence_fields")
                claims=[next((x for x in reversed(claims) if x[0].get("quote") is not None),claims[-1])]
    if claims:return finish_result(spec,claims,"structured_claim")
    if is_extract and re.fullmatch(r"(?is)\s*<quote>.*?</quote>>?\s*",s):return r.result(r.MISSING,"missing_answer_field")
    if is_delivery and isinstance(obj,dict) and "answer" not in obj:return r.result(r.MISSING,"missing_answer_field")
    if re.search(r"(?m)^\s*\{",s) or s.startswith(("{","[",r"\{","$$")):return r.result(r.MISSING,"malformed_structured_payload")
    return r.result(r.MISSING,"no_complete_structured_claim")

def literal(spec,s):
    import recovery as r
    fam=spec.get("family")
    lines=[l.strip() for l in s.splitlines() if l.strip()]
    patterns={
        "leading_zero":r"[0-9]+\.?",
        "literal_case":r"[A-Za-z0-9_-]+\.?",
        "unicode":r"[^\s]+",
        "tsv":r"[A-Za-z0-9_-]+(?:[\t ,;\\]+|\\t)[0-9]+(?:[\t ,;\\]+|\\t| TAB )[0-9]+(?:\.| TAB)?",
        "csv_quoted":r"[A-Za-z0-9_\"-]+\s*[,|:][^\n]+[,|]\s*\"?[0-9]+\"?\.?",
        "multiline":r"\[?[A-Za-z]+=[A-Za-z0-9_-]+\]?\s+\[?[A-Za-z]+=[A-Za-z0-9_-]+\]?",
        "xml":r"(?:<|to)[A-Za-z]+ [^\n]+</[A-Za-z]+>",
    }
    p=patterns.get(fam)
    if p is None:return r.result(r.MISSING,"unsupported_literal_family")
    if re.fullmatch(p,s.strip()):
        return finish_result(spec,[(s,s,"literal_preserve_representation")],"literal_delivered")
    claims=[]
    if fam in ("tsv","csv_quoted") and len(lines)==3 and re.fullmatch(r'"?[A-Za-z0-9_-]+"?',lines[0]) and re.fullmatch(r'"?[0-9]+"?',lines[-1]):
        return finish_result(spec,[(s,s,"wrong_literal_delimiters")],"literal_delivered")
    if fam=="multiline" and len(lines)>=2:
        for i in range(len(lines)-1):
            v="\n".join(lines[i:i+2])
            if re.fullmatch(p,v):claims.append((v,v,"multiline_literal"))
    for l in lines:
        if re.fullmatch(p,l):claims.append((l,l,"literal_line"))
        else:
            m=re.fullmatch(r"(?i)(?:content|output|result|final(?: answer)?|return)\s*:\s*(.+)",l)
            if m and re.fullmatch(p,m[1]):claims.append((m[1],l,"literal_declaration"))
    if claims:return finish_result(spec,claims,"literal_claim")
    if fam in ("tsv","csv_quoted") and any(re.fullmatch(r'"?[A-Za-z0-9_-]+"?',l) for l in lines) and any(re.fullmatch(r'"?[0-9]+"?',l) for l in lines):
        return r.result(r.MISSING,"multiple_or_malformed_literal_records")
    if re.search(r"(?i)\b(?:placeholder|content not found|no output|cannot (?:provide|return)|this is a single line response)\b",s):return r.result(r.MISSING,"explicit_no_answer")
    if re.match(r"(?i)^copy this case-sensitive identifier exactly:",s):
        return r.result(r.MISSING,"instruction_echo_without_claim")
    return r.result(r.MISSING,"literal_payload_unidentified")

MORE_PATTERNS={
"integer":[
 r"(?:the )?(?:result of (?:the )?(?:given )?(?:calculation|computation|expression)(?: \([^;]+\))?|integer(?: value| it returns| [AB] sees)?|final value read by [AB]|offset(?: field)? of the last (?:outgoing )?subfragment|offset|prefix length|final count|correct number of distinct arrangements(?: that satisfy all the given constraints)?|minimum total cost from A to D|number of (?:outgoing IPv4 fragments|accepted tokens|authorized requests)|total number of authorized requests|(?:cumulative|final cumulative) ACK(?: number| value)?(?: after the last segment| \(unsigned decimal\))?|ACK number (?:sent )?after the last segment|remaining TTL(?: at t=[0-9]+ seconds| after [0-9]+ seconds)?|maximum (?:new )?(?:data )?bytes sendable (?:now|after processing it)|maximum sendable now)\s*(?:is(?: therefore)?|should be|would be|:|=)\s*(.+)",
 r"(?:the )?remainder when .+? is divided by [0-9]+ is (.+)",
 r"[0-9.]+/[0-9]+ has (.+?) usable host addresses",
 r"(?:there are|there is) ("+INT+r") requests authorized",
 r"(?:the )?first time both machines run together is at (.+)",
 r"(?:the )?integer representing the first time both machines run together is (.+)",
 r"("+INT+r")\s+tokens are accepted",
 r"(?:none|no tokens) (?:are accepted|is accepted)",
 r"(?:(?:the )?ACK number (?:sent )?after the last segment (?:is|would be) |(?:the )?cumulative ACK number is )("+INT+r")(?:[, ]+as .+| \(.+\))",
],
"hex4":[r"(?:the )?high 16-bit half(?: of .+?)? is (.+)",r"(?:the )?high 16-bit half\s*:\s*(.+)"],
"interface":[r"(?:the )?(?:correct|selected|requested) interface(?: for the interface .+?)? is (.+)",r"(?:the )?interface selected is\s*:?\s*(.+)",r"(.+?) interface is selected",r"(?:the )?interface selected is the one associated with .+?, which is (?:interface )?(.+)"],
"octal":[r"(?:the )?(?:final four-digit octal permission mode|resulting 4-character octal mode|octal|permission bits|requested permission bits(?: after .+?)?) (?:is|are) (.+)"],
"bitstring":[r"(?:the )?(?:exact [0-9]+ binary digits that indicate acceptance|binary representation of the expired records in the original order|binary digits representing expired records at t=[0-9]+|final node eligibility)\s*(?:are|is|:)\s*(.+)"],
"text2":[r"(?:the )?(?:requested |exact )?two (?:ASCII )?characters(?: in the(?: answer)?| that are read(?: from .+?)?)?\s*(?:are|is)\s*:?\s*(.+)",r"(?:the )?two[- ]character string in the (?:[\x60'\"]?answer[\x60'\"]? variable|answer|)\s*(?:is|are)\s*:?\s*(.+)"]
}

FAMILY_CONCLUSIONS={
    "path":[r"minimum total cost(?: from [A-Z] to [A-Z])?\s*:\s*(.+)"],
    "tcp-send-window":[
        r"(?:the )?maximum new (?:data |payload )?bytes (?:sendable after processing (?:the )?cumulative ACK|that can be sent) (?:is|are) (.+)",
        r"(?:the )?maximum new (?:data |payload )?bytes that can be sent is the minimum of [0-9]+B and [0-9]+B, which is (.+)",
        r"(?:the )?(?:sender can send|calculation is) (.+)",
    ],
    "ipv4-cidr-boundaries":[r"(?:the )?usable host addresses (?:are|is) (.+)",r"(?:the )?last octet is (.+)"],
    "ipv4-fragment-offset":[r"(?:the )?number of outgoing IPv4 fragments required is (.+)"],
    "dns-ttl-chain":[r"([0-9]+ seconds) of TTL remain",r"(?:the )?binary representation of (?:the expiry status for the records in the original order|this result) is ([01]+)"],
    "sqlite-left-join-null":[r"(?:the )?(?:query will return|result of the query is|integer returned by the query is) ([+-]?[0-9]+)(?: rows)?"],
    "sqlite-window-frames":[r"(?:the )?integer returned by the query is ([+-]?[0-9]+)"],
    "sqlite-wal-snapshots":[r"(?:connection )?[AB] reads the integer ([+-]?[0-9]+)"],
    "posix-file-offsets":[r"(?:the )?(?:exact )?two ASCII characters in (?:the )?[\x60'\"]?answer[\x60'\"]? (?:are|is) (.+)"],
}

def conclusion_head(z):
    if HEAD.fullmatch(z):return True
    if re.fullmatch(r"(?i)(?:(?:so|thus|therefore|hence|following .+?),?\s*)?(?:the\s+)?(?:correct(?: and only)? answer(?: to return)?|final answer|final result(?: of the query)?|answer|result(?: returned by the query)?|verified solution|requested (?:value|information)|remainder when .+? is divided by [0-9]+|integer returned|permission bits|high 16-bit half|final node eligibility|(?:exact |requested )?[0-9]+ binary digits.*|requested value.*|the two ASCII characters.*|two ASCII characters.*|answer without any.*)\s*(?:is|are|is therefore)?\s*:",z):
        return True
    return bool(re.search(r"(?i)\b(?:the (?:final |correct )?answer|the requested value|the final result|the requested permission bits when .+?)\s*(?:is|are|without any .+?)?\s*:\s*$",z))

def ordered_bits(s):
    rows=[]
    explicit_rows=[]
    for line in s.splitlines():
        z=strip_markdown(line)
        m=re.fullmatch(r"(?i)node\s+([1-9][0-9]*)\s+\(n([1-9][0-9]*)\)\s*:\s*([01])",z)
        if m and m[1]==m[2]:explicit_rows.append((int(m[1]),m[3],z))
    if len(explicit_rows)>=2 and [i for i,_,_ in explicit_rows]==list(range(1,len(explicit_rows)+1)):
        return [("".join(b for _,b,_ in explicit_rows),"\n".join(z for _,_,z in explicit_rows),"ordered_node_statuses")]
    blocks=list(re.finditer(r"(?im)^\s*([1-9][0-9]*)\.\s*Namespace:[^\n]+\n\s*-\s*Response:\s*([01])\s*\((Authorized|Denied)\)\s*$",s))
    if len(blocks)>=2 and [int(m[1]) for m in blocks]==list(range(1,len(blocks)+1)) and all((m[2]=="1")== (m[3].lower()=="authorized") for m in blocks):
        return [("".join(m[2] for m in blocks),"\n".join(m[0] for m in blocks),"ordered_response_fields")]
    if re.search(r"(?im)^here are the binary digits for the requested values:",s):
        parts=[l.strip() for l in s.splitlines() if l.strip()]
        matches=[re.fullmatch(r"(?i)([01])\.\s*(authorized|denied)\s*\([^\n]+\)",z) for z in parts[1:]]
        if len(matches)>=2 and all(matches) and all((m[1]=="1")== (m[2].lower()=="authorized") for m in matches):
            return [("".join(m[1] for m in matches),"\n".join(parts[1:]),"explicit_status_digit_rows")]
    for l in s.splitlines():
        z=strip_markdown(l)
        m=re.fullmatch(r"(?i)(?:node\s+)?([1-9][0-9]*)(?:\.|\s+\(n[0-9]+\)|\s+\(id=[^)]*\)|\s*:)\s*(?:node n[0-9]+:\s*)?(?:(?:eligible|ineligible|authorized|denied|expired|not expired)\s*\(([01])\)|(?:\(([01])\)\s*)?([01])(?:\s*\([^)]*\))?|.+?\s*(?:->| - )\s*(?:authorized|denied|eligible|ineligible)\s*\(([01])\)|.+?\s*->\s*([01])\s*\([^)]*\)|((?:in)?eligible|authorized|denied|accepted|rejected))",z)
        if not m:continue
        bits=[x for x in m.groups()[1:6] if x is not None]
        if len(set(bits))>1:continue
        if bits:v=bits[0]
        elif m[7]:v="1" if m[7].lower() in ("eligible","authorized","accepted") else "0"
        else:continue
        rows.append((int(m[1]),v,z))
    groups=[];current=[]
    for x in rows:
        if current and x[0]!=current[-1][0]+1:
            if len(current)>=2 and current[0][0]==1:groups.append(current)
            current=[]
        if x[0]==1 or current:current.append(x)
    if len(current)>=2 and current[0][0]==1:groups.append(current)
    return [("".join(x[1] for x in g),"\n".join(x[2] for x in g),"ordered_explicit_statuses") for g in groups]

def phrase_claim(spec,line):
    import recovery as r
    fmt=spec.get("format") or ("integer" if spec.get("kind")=="delivery" else None)
    z=strip_markdown(line).strip()
    z=re.sub(r"(?i)^\s*[-*]\s*","",z)
    z=re.sub(r"(?i)^explanation:\s*(?=(?:the\s+)?(?:correct|final)\s+answer\b)","",z)
    if not z:return r.MISSING,"empty"
    m=re.fullmatch(r"(?i)"+LABEL+r"\s*:\s*(.+)",z)
    if m:
        v,rule=payload(spec,m[1])
        if v is not r.MISSING:return v,"explicit_label_"+rule
        z=m[1]
    sentences=re.split(r"(?<=[.!?])\s+(?=[A-Z])",z)
    for x in [z,*reversed(sentences)]:
        x=re.sub(r"(?i)^(?:so|therefore|thus|hence|accordingly)[,]?\s+","",x.strip())
        mathlabel=re.fullmatch(r"\\text\{(?i:FINAL|ANSWER):\s*("+INT+r")\}",x)
        if mathlabel and fmt=="integer":return str(int(mathlabel[1])),"latex_labeled_integer"
        tail=re.fullmatch(r"(?i)here is the final answer without any (?:further )?(?:explanation|labels?)(?: or (?:labels?|explanation))?\s*:\s*(.+)",x)
        if tail:
            v,rule=payload(spec,tail[1])
            if v is not r.MISSING:return v,"terminal_answer_phrase_"+rule
        if fmt=="integer":
            m=re.fullmatch(r"(?i)(?:the )?result of (?:the )?(?:given )?(?:calculation|computation|expression)\s+[0-9() +*/^−×÷-]+\s+is ("+INT+r")\.?",x)
            if m and spec.get("family")=="arithmetic":return str(int(m[1])),"explicit_arithmetic_result"
            m=re.fullmatch(r"(?i)(?:connection )?[AB] will read the (?:original|updated|current) value of v, which is ("+INT+r")\.?",x)
            if m and spec.get("family")=="sqlite-wal-snapshots":return str(int(m[1])),"explicit_read_value"
            m=re.fullmatch(r"(?i)return\s+("+INT+r")\.?$",x)
            if m:return str(int(m[1])),"unlabeled_return"
            m=re.fullmatch(r"(?i).+?which gives a total of ("+INT+r")\.?",x)
            if m and spec.get("family")=="jwt-boundary-validation":return str(int(m[1])),"explicit_token_count"
            m=re.fullmatch(r"(?i)(?:returning only the integer,\s*)?(?:the )?(?:result|correct result) is ("+INT+r")\.?",x)
            if m:return str(int(m[1])),"explicit_integer_result"
            m=re.fullmatch(r"(?i)(?:the )?additional bytes it can send are ("+INT+r") bytes\.?",x)
            if m and spec.get("family")=="tcp-send-window":return str(int(m[1])),"explicit_send_window"
            m=re.fullmatch(r"(?i)(?:the )?cumulative ACK number it should send is ("+INT+r")\.?",x)
            if m:return str(int(m[1])),"explicit_ack"
            m=re.fullmatch(r"(?i)(?:the )?requested integer returned is ("+INT+r")\.?",x)
            if m:return str(int(m[1])),"explicit_integer"
        if fmt=="bitstring":
            m=re.fullmatch(r"(?i)the exact [0-9]+ binary digits that indicate acceptance are:\s*([01]+)\.?",x)
            if m:return m[1],"explicit_bit_output"

        x=re.sub(r"(?i)^(?:so|therefore|thus|hence|accordingly)[,]?\s+","",x.strip())
        x=x.strip().rstrip(".")
        if NEGATIVE.search(x):continue
        m=CONCLUSION.fullmatch(x)
        if m:
            v,rule=payload(spec,m[1])
            if v is not r.MISSING:return v,"conclusion_"+rule
        for p in FAMILY_CONCLUSIONS.get(spec.get("family"),[])+FORMAT_PATTERNS.get(fmt,[])+MORE_PATTERNS.get(fmt,[]):

            m=re.fullmatch(p,x,re.I)
            if m:
                if not m.groups() and fmt=="integer" and spec.get("family") in ("jwt-boundary-validation","kubernetes-rbac-scope"):
                    return "0","explicit_zero_count"
                if not m.groups():continue
                v,rule=payload(spec,m[1])
                if v is not r.MISSING:return v,"format_conclusion_"+rule
        if fmt=="integer":
            m=re.fullmatch(r"(?i).*?\b(?:so|therefore|thus|hence)[,]?\s+(?:the )?minimum total cost is ("+INT+r")",x)
            if m:return str(int(m[1])),"concluding_cost"
    return r.MISSING,"no_phrase"

def scalar_claims(spec,s,original):
    import recovery as r
    lines=[];inside=False
    for line in s.splitlines():
        if re.fullmatch(r"\s*\x60{3}(?:[A-Za-z0-9_-]+)?\s*",line):
            inside=not inside;continue
        lines.append((strip_markdown(line),inside))
    nonempty=[(l,f) for l,f in lines if l]
    if not nonempty:return r.result(r.MISSING,"no_visible_answer")
    claims=[];explicit=[];bare=[];pending=False;bad_explicit=False
    for i,(z,f) in enumerate(nonempty):
        if conclusion_head(z):
            pending=True;continue
        if pending and z in ("$$",r"\[",r"\]","---"):
            continue
        if fmt_math:=re.fullmatch(r"\\boxed\{([^{}]+)\}",z):
            if pending:
                v,rule=payload(spec,fmt_math[1])
                if v is not r.MISSING:
                    explicit.append((v,z,"boxed_terminal_"+rule));pending=False;continue
        v,rule=phrase_claim(spec,z)
        if v is not r.MISSING:
            explicit.append((v,z,rule));pending=False
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])",z):
                if sentence==z:continue
                if not re.match(r"(?i)^(?:(?:so|thus|therefore|hence)[,]?\s+)?(?:the\s+)?(?:final answer|correct answer|answer|final result)\s+(?:is|equals)",sentence):continue
                v2,rule2=phrase_claim(spec,sentence)
                if v2 is not r.MISSING:explicit.append((v2,sentence,rule2))
            continue
        v,rule=payload(spec,z)
        if pending and v is not r.MISSING:
            explicit.append((v,z,"after_answer_heading_"+rule));pending=False
            continue
        if pending:
            pending=False
        if v is not r.MISSING:
            bare.append((i,v,z,rule))
        if re.fullmatch(r"(?i)"+LABEL+r"\s*:\s*.+",z):
            if not re.search(r"(?i)^(?:return|output|final)\s*:\s*(?:followed by|exactly|only|the requested|the following|no other)",z):
                bad_explicit=True
    if spec.get("format")=="bitstring":
        if re.fullmatch(r"(?:\s*\[[01]\]\s*)+",s):
            return finish_result(spec,[("".join(re.findall(r"\[([01])\]",s)),s,"bracketed_bit_sequence")],"ordered_bit_sequence")
        if bare and bare[0][3]=="explicit_status_sequence" and bare[0][0]==0:
            first=bare[0][1]
            tail=nonempty[-1][0]
            if (set(first)=={"1"} and re.match(r"(?i)^all (?:nodes|requests|tokens|records) are (?:eligible|authorized|accepted|expired)\b",tail)) or (set(first)=={"0"} and re.match(r"(?i)^(?:all (?:nodes|requests|tokens|records) are (?:ineligible|denied|rejected)|none .+? (?:eligible|authorized|accepted|expired))\b",tail)):
                explicit.append((first,bare[0][2],"explicit_status_sequence"))
        explicit.extend(ordered_bits(s))
        # A complete sequence of individually bracketed bits is a representation, not competing declarations.
        if re.fullmatch(r"(?:\s*\[[01]\]\s*)+",s):
            explicit.append(("".join(re.findall(r"\[([01])\]",s)),s,"bracketed_bit_sequence"))
    if explicit:
        if re.search(r"(?i)\b(?:still need to (?:check|calculate|solve|decide)|not (?:a|the) final answer|remaining (?:cases|possibilities) have not been|work is not finished)\b",nonempty[-1][0]):
            return r.result(r.MISSING,"unfinished_reasoning")
        claims=explicit
        if spec.get("mode")=="strict" and bare and bare[0][0]==0 and bare[0][3]!="equation_rhs" and not (len(bare)>=2 and bare[1][0]==1 and any(re.match(r"(?i)final\s+ack|final cumulative ack",x[1]) for x in explicit)):

            claims=[(bare[0][1],bare[0][2],"answer_first"),*claims]
        if NEGATIVE.search(nonempty[-1][0]) and phrase_claim(spec,nonempty[-1][0])[0] is r.MISSING:
            return r.result(r.MISSING,"uncertain_claim")
        if original["method"] in ("conflicting_declarations","conflicting_json_keys") and len(explicit)<2:
            return original
        if bad_explicit and len(claims)==1 and not (original["method"]=="malformed_declaration" and nonempty[-1][0]==claims[-1][1]):
            return r.result(r.MISSING,"ambiguous_malformed_declaration")
        return finish_result(spec,claims,"explicit_claim_recovery")
    if original["method"] in ("conflicting_declarations","conflicting_json_keys"):return original
    if bare:
        if all(i==k for k,(i,_,_,_) in enumerate(bare)) and len(bare)==len(nonempty):
            return finish_result(spec,[(v,z,m) for _,v,z,m in bare],"repeated_or_conflicting_values")
        if spec.get("mode")=="strict" and bare[0][0]==0 and not bad_explicit and not NEGATIVE.search(nonempty[-1][0]):
            rest=" ".join(z for z,_ in nonempty[1:])
            if re.search(r"(?i)\b(?:explanation|reasoning|because|the (?:answer|result|value|requested|connection|given|selected)|this is|this means|as requested)\b|\bnote\s*:",rest):
                return finish_result(spec,[(bare[0][1],bare[0][2],"answer_first")],"answer_with_explanation")
        if len(bare)>=2 and bare[-1][0]==len(nonempty)-1 and key(spec,bare[-1][1])==key(spec,bare[-2][1]):
            return finish_result(spec,[(bare[-1][1],bare[-1][2],"repeated_terminal_value")],"repeated_terminal_value")
    if spec.get("format")=="integer" and spec.get("family")=="ipv4-fragment-offset":
        m=re.fullmatch(r"(?i)(?:[0-9]+B\s*[+\-]\s*)+[0-9]+B\s*=\s*("+INT+r")B\s*\n\s*("+INT+r")",s)
        if m and m[1]==m[2]:return finish_result(spec,[(str(int(m[2])),m[0],"repeated_equation_result")],"explicit_equation_result")
    if spec.get("format")=="integer" and spec.get("family")=="jwt-boundary-validation":
        m=re.fullmatch(r"(?i)("+INT+r")\s+tokens are accepted\.?",s)
        if m:return finish_result(spec,[(str(int(m[1])),s,"split_token_count")],"explicit_count")
    if spec.get("format")=="csv_none" and re.fullmatch(r"(?i)none\.?\s+return\s+\[\]\s*;?",s):
        return finish_result(spec,[("NONE",s,"explicit_empty_sequence")],"explicit_empty_sequence")
    if spec.get("format")=="bitstring" and bare and bare[0][0]==0 and bare[0][3]=="explicit_status_sequence" and len(bare)==1 and re.search(r"(?i)\b(?:final result is determined to be accepted|output is a single binary digit representing acceptance)\b",s):
        return finish_result(spec,[(bare[0][1],bare[0][2],"explicit_single_status")],"explicit_status")
    if spec.get("family")=="arithmetic" and len(nonempty)>=2:
        v,rule=payload(spec,nonempty[-1][0])
        previous=nonempty[-2][0]
        m=re.fullmatch(r"(?i)(?:now add|add the (?:two )?results|total|sum)\s*:\s*([0-9 +*/()−-]+=[0-9 +*/()−-]+)",previous)
        if m and v is not r.MISSING:
            v2,_=payload(spec,m[1])
            if v2 is not r.MISSING and key(spec,v)==key(spec,v2):
                return finish_result(spec,[(v,nonempty[-1][0],"terminal_scalar_matches_explicit_sum")],"corroborated_terminal_scalar")
    if spec.get("format")=="hex4" and spec.get("family")=="endian-signed-bitfields" and len(nonempty)>=2:
        lhs,sep,rhs=nonempty[-1][0].rpartition("=")
        if sep and re.fullmatch(r"[()X0-9A-F >^&ORND]+",lhs,re.I) and re.search(r"\b(?:XOR|AND)\b|[&^]",lhs,re.I) and re.fullmatch(r"[0-9A-F]+",rhs.strip(),re.I):
            v,rule=payload(spec,rhs.strip())
            if v is not r.MISSING:
                return finish_result(spec,[(v,nonempty[-1][0],"terminal_bitwise_expression_rhs")],"explicit_bitwise_result")
    if NEGATIVE.search(nonempty[-1][0]):return r.result(r.MISSING,"uncertain_claim")
    if re.search(r"(?im)^no output\.?\s*$",s) and re.search(r"(?im)^return exactly(?: one line)?\s*:\s*(?:final:\s*)?[+-]?[0-9]+\.?\s*$",s):
        return r.result(r.MISSING,"conflicting_answer_directives")
    if re.search(r"(?i)\b(?:i cannot provide|i cannot answer|no output|no answer|cannot be determined|not enough information|insufficient information|none of the requested (?:value|characters)|no solution provided)\b",s):
        return r.result(r.MISSING,"explicit_no_answer")
    if re.fullmatch(r"(?i)(?:all|none of the) (?:nodes|requests|tokens|records) (?:are|is) (?:eligible|accepted|authorized|expired).*",nonempty[-1][0]):
        return r.result(r.MISSING,"descriptive_answer_not_encoded")
    if re.search(r"(?i)final answer: the two characters that were read from the file are the two characters that were read",s):
        return r.result(r.MISSING,"tautological_answer")
    if spec.get("kind")=="delivery" and re.search(r"(?im)^return none\.?\s*$",s) and re.search(r"(?m)^0\s*$",s):
        return r.result(r.MISSING,"conflicting_declarations")
    if spec.get("kind")=="delivery" and re.search(r"(?i)you are not being asked to solve again",s):
        return r.result(r.MISSING,"instruction_echo_without_claim")
    if spec.get("kind")=="delivery" and bare and bare[0][0]==0 and re.search(r"(?i)the initial balance",s):
        return r.result(r.MISSING,"answer_or_intermediate_ambiguous")
    if spec.get("format")=="bitstring" and re.search(r'(?m)^\s*\["n[0-9]+"(?:,\s*"n[0-9]+")*\]\s*$',s):
        return r.result(r.MISSING,"wrong_structured_answer_type")
    if bad_explicit:return r.result(r.MISSING,"malformed_declaration")
    if spec.get("format")=="bitstring" and s.startswith(("{","[")) and s.endswith(("}","]")):
        try:
            obj=json.loads(s)
            if isinstance(obj,(dict,list)):return r.result(r.MISSING,"wrong_structured_answer_type")
        except ValueError:
            return r.result(r.MISSING,"malformed_structured_payload")
    if len(nonempty)>=2 and len({z for z,_ in nonempty})<=2 and all(z.endswith("?") or re.match(r"(?i)^let us restate",z) for z,_ in nonempty):
        return r.result(r.MISSING,"repeated_question_without_answer")

    if any(re.search(r"(?i)\b(?:return only|return exactly|requested output format|end with|the requested representation)\b",z) for z,_ in nonempty) and not claims:
        return r.result(r.MISSING,"instruction_echo_without_claim")
    if len(nonempty)==1 and spec.get("format")=="integer" and re.search(r"\b[0-9]+B\.?$",nonempty[0][0],re.I):
        return r.result(r.MISSING,"unsupported_answer_unit")
    if len(nonempty)==1 and re.fullmatch(r"(?i)\((?:minimum total cost|requested value|answer|result)(?: from [A-Z] to [A-Z])?\)",nonempty[0][0]):
        return r.result(r.MISSING,"placeholder_without_answer")
    return original

def recover_extended(spec,reply,original):
    import recovery as r
    if original["status"]!="unresolved" or reply.get("finish_reason")!="stop" or reply.get("tool_calls"):return original
    raw=reply.get("content")
    if not isinstance(raw,str):return original
    s=clean_visible(raw)
    if not s:
        if r.BLOCKED.search(raw):return original
        if original["method"]=="special_marker_inside_response" and re.search(r"(?im)^\s*(?:#{1,6}\s+)?(?:\*\*)?final(?: answer)?\s*:",raw):
            z=re.sub(r"</?think>","",raw,flags=re.I)
            z=r.ROLE.sub("",z.strip(),count=1)
            if not r.BLOCKED.search(z):s=z.strip()
        if not s:return original
    if original["method"]=="empty_declaration" and re.fullmatch(r"(?i)\s*"+LABEL+r"\s*:\s*",s):return original
    if original["method"]=="uncertain_claim" and re.search(r"(?i)\b(?:might be|could be|not sure|cannot choose|cannot decide|if .+? then)\b",s.splitlines()[-1]):
        return original
    if original["method"]=="example_or_unendorsed_declaration":return original
    if spec.get("kind")=="protocol" and spec.get("format")=="exact":return literal(spec,s)
    if spec.get("kind")=="extraction" or spec.get("format")=="json" or spec.get("contract")=="json":
        return structured(spec,s)
    if spec.get("format")=="interface":
        m=re.fullmatch(r"(?is)(?:final(?: answer)?\s*:\s*)?([0-9.]+/[0-9]+\s*,\s*[0-9]+\s*,\s*if[0-9]+)\s*;\s*(.+)",s)
        if m:
            v,rule=payload(spec,m[1])
            if v is not r.MISSING:
                v2,rule2=payload(spec,m[2].removesuffix(" is selected."))
                if v2 is not r.MISSING:return finish_result(spec,[(v,m[1],rule),(v2,m[2],rule2)],"route_tuple_claims")
    correction=re.match(r"(?is)^([^\n]+)\n\s*(Wait,\s*(?:no\b[^\n]*|let me (?:compute|calculate|recalculate) correctly\.?))\n+(.+)$",s)
    if correction and spec.get("mode")=="strict":
        old,oldrule=payload(spec,correction[1])
        if old is not r.MISSING:
            suffix=correction[3].strip()
            sub=r.recover_primary(spec,{"content":suffix,"finish_reason":"stop"})
            if sub["status"]=="unresolved":
                sub=scalar_claims(spec,suffix,sub)
            if sub["status"]=="recovered":
                return {**sub,"method":"explicit_self_correction","withdrawn_candidate":old,"withdrawal_text":correction[2],"steps":[*sub.get("steps",[]),"explicit_initial_answer_withdrawal"]}
    v,rule=payload(spec,s)
    if v is not r.MISSING:
        return finish_result(spec,[(v,s,rule)],"whole_answer_representation")
    return scalar_claims(spec,s,original)
