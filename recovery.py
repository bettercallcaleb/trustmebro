import argparse
import collections
import json
import math
import re
from pathlib import Path

VERSION="answer-recovery-v0.4"
MISSING=object()
LABEL=re.compile(r"(?i)^(?:final(?: answer| result)?|answer|return|result|solution|corrected answer|output)\s*:\s*(.*)$")
HEADING=re.compile(r"^#{1,6}\s+")
FENCE=re.compile(r"\x60{3}(?:[A-Za-z0-9_-]+)?[ \t]*\n(.*?)\n\x60{3}",re.S)
INTEGER=re.compile(r"[+-]?[0-9]{1,30}")
EQUATION=re.compile(r"[0-9+\-*/^%(). ×÷−\t]+(?:=[0-9+\-*/^%(). ×÷−\t]+)+")
FINAL_PHRASE=re.compile(r"(?i)^(?:so[,]?\s+|therefore[,]?\s+|thus[,]?\s+|hence[,]?\s+)?(?:the\s+)?(?:final answer|correct answer|answer|final result|result|remainder|requested (?:value|number|answer)|minimum (?:total )?cost|selected interface|correct interface|interface selected|integer returned|integer [AB] reads|output|first positive minute (?:at which|when) both machines run together|maximum (?:number of )?(?:new )?(?:data |payload )?bytes|number of usable host addresses)\s+(?:is|equals)\s*:?\s*(.+)$")
READS=re.compile(r"(?i)^(?:connection\s+)?[AB]\s+reads\s+(.+)$")
ROLE=re.compile(r"(?i)^(?:assistant\s*:\s*|assistant\s*\n|<\|im_start\|>assistant\s*|<\|assistant\|>)")
BLOCKED=re.compile(r"(?i)<(?:/?tool_(?:call|response)|/?function[=>])|<\|(?:user|system|im_start)\|>")
UNCERTAIN=re.compile(r"(?i)\b(?:not sure|not verified|not yet|cannot (?:choose|decide)|remain(?:s)? (?:uncertain|possible)|retract|withdraw|do not know|haven't decided|might be|could be|would be|if .*then)\b")
TYPE_FIELDS=("kind","format","family","contract","mode")
STRATEGIES={
 "alternative_label":"explicit_declaration","bit_delimiter":"normalize_bit_separators","bit_width":"retain_complete_wrong_width","code_fence":"unwrap_balanced_wrapper","contract_violation":"preserve_original_contract_score","csv_length_mismatch":"retain_complete_sequence","csv_space":"normalize_csv_separators","duplicate_json_keys":"collapse_identical_keys_only","empty_final_label":"inspect_adjacent_value_or_abstain","empty_output":"abstain_no_answer","error_code_width":"retain_complete_wrong_width","extra_outer_whitespace":"preserve_literal_contract","extra_text":"terminal_explicit_commitment_only","false_extraction":"retain_extracted_claim","hex_width":"retain_complete_wrong_width","inline_code":"unwrap_balanced_wrapper","invalid_json":"parse_complete_json_or_abstain","irrelevant_quote":"retain_claim_evaluate_evidence_separately","json_abstention":"explicit_abstention","json_array_length_mismatch":"retain_complete_json","json_key_set_mismatch":"retain_complete_json","json_type_mismatch":"retain_typed_json","leading_role_marker":"strip_assistant_prefix_only","length_limit":"abstain_unless_repeated_complete_declarations","literal_mismatch":"retain_literal","malformed_declaration":"bounded_declaration_parser","markdown_emphasis":"unwrap_balanced_wrapper","markdown_wrapper":"unwrap_balanced_wrapper","missing_keys":"retain_claim_if_present","missing_quote":"retain_claim_evaluate_evidence_separately","multiple_declarations":"require_consistent_commitments","noncanonical_abstention":"explicit_abstention","noncanonical_label":"explicit_declaration","nonterminal_declaration":"abstain_if_subsequent_text","octal_width":"retain_complete_wrong_width","periodic_numeric_output":"retain_complete_sequence_or_abstain_if_truncated","quote_not_in_source":"retain_claim_evaluate_evidence_separately","repeated_answer_declaration":"collapse_identical_complete_declarations","repeated_thinking_marker":"strip_orphan_closing_prefix_only","representation_deviation":"normalize_representation_without_guessing","tab_to_comma_substitution":"retain_wrong_literal","tag_error":"retain_claim_preserve_contract","thinking_marker_in_visible_output":"strip_thought_boundary_only","tool_marker_in_visible_output":"abstain_tool_content","truncated_declaration_prefix":"require_repeated_identical_complete_declarations","unresolved_decision":"conservative_recovery_or_abstain","value_used_as_key":"retain_wrong_structure","wrong_answer_type":"safe_integer_field_conversion_only","wrong_output_entity_cidr":"retain_wrong_entity","wrong_value":"retain_claim","conflicting_declarations":"abstain_conflict","case_only_mismatch":"preserve_literal_case","unicode_normalization_difference":"preserve_literal_unicode","leading_zero_loss":"preserve_literal_width","repeated_csv_value":"retain_complete_sequence"
}

def public_spec(task):
    return {k:task[k] for k in TYPE_FIELDS if k in task}

def canonical(v):
    return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)

def unwrap(s):
    s=s.strip()
    for _ in range(5):
        old=s
        f=FENCE.fullmatch(s)
        if f:s=f.group(1).strip()
        else:
            for a,b in (("**","**"),("__","__"),("\x60","\x60"),("$","$"),('"','"'),("'","'")):
                if a in ('"',"'"):continue
                if s.startswith(a) and s.endswith(b) and len(s)>len(a)+len(b) and a not in s[len(a):-len(b)]:
                    s=s[len(a):-len(b)].strip();break
        if old==s:break
    m=re.fullmatch(r"\\boxed\{([^{}]+)\}",s)
    if m:s=unwrap(m[1])
    return s

def json_parse(s):
    duplicate=False
    def pairs(items):
        nonlocal duplicate
        d={}
        for k,v in items:
            if k in d:
                if canonical(d[k])!=canonical(v):raise ValueError("conflicting_json_keys")
                duplicate=True
            d[k]=v
        return d
    def invalid(x):raise ValueError("nonfinite_json")
    def flt(x):
        v=float(x)
        return v if math.isfinite(v) else invalid(x)
    try:
        v=json.loads(s,object_pairs_hook=pairs,parse_constant=invalid,parse_float=flt)
        return v,"identical_duplicate_keys" if duplicate else "json"
    except (ValueError,TypeError,OverflowError,RecursionError) as e:
        return MISSING,"conflicting_json_keys" if str(e)=="conflicting_json_keys" else "invalid_json"

def int_value(s):
    if type(s) is int:return str(s)
    if isinstance(s,str) and INTEGER.fullmatch(s):return str(int(s))
    return MISSING

def parse_value(spec,s,declared=False):
    s=unwrap(s)
    kind=spec.get("kind","reasoning");fmt=spec.get("format")
    contract=spec.get("contract")
    if kind=="extraction" or contract=="json" or fmt=="json":
        if kind=="extraction" and s.upper()=="UNKNOWN":return {"decision":"abstain"},"explicit_abstention"
        if s.startswith("$$") and s.endswith("$$"):
            z=s[2:-2].strip()
            if z.startswith(r"\{") and z.endswith(r"\}"):s="{"+z[2:-2]+"}"
        value,reason=json_parse(s)
        if value is MISSING:return MISSING,reason
        if kind=="extraction":
            if isinstance(value,dict):
                ans=value.get("answer")
                if isinstance(ans,str) and ans.strip().upper()=="UNKNOWN" and set(value)<={"answer","quote"}:return {"decision":"abstain"},"json_abstention"
                iv=int_value(ans)
                if iv is not MISSING:return {"decision":"extract","answer":iv,"quote":value.get("quote")},reason
            if type(value) is int or isinstance(value,str):
                iv=int_value(value)
                if iv is not MISSING:return {"decision":"extract","answer":iv,"quote":None},"bare_extracted_integer"
            return MISSING,"no_extraction_claim"
        if contract=="json":
            if isinstance(value,dict):
                iv=int_value(value.get("answer"))
                if iv is not MISSING:return iv,reason
            return MISSING,"no_answer_field"
        if kind!="protocol" and isinstance(value,dict) and type(value.get("count")) is str and INTEGER.fullmatch(value["count"]):
            value={**value,"count":int(value["count"])}
            return value,"core_count_type_conversion"
        return value,reason
    if kind=="protocol" or fmt=="exact":
        return s,"literal"
    if kind=="delivery":fmt="integer"
    if fmt=="integer":
        iv=int_value(s)
        if iv is not MISSING:return iv,"scalar"
        if re.fullmatch(r"[+-]?[1-9][0-9]{0,2}(?:,[0-9]{3})+",s):
            return str(int(s.replace(",",""))),"grouped_integer"
        if spec.get("family")=="ipv4-cidr-boundaries" and re.fullmatch(r"/[0-9]{1,2}",s):return s[1:],"cidr_prefix_notation"
        if spec.get("family")=="tcp-send-window":
            m=re.fullmatch(r"([+-]?[0-9]{1,30})\s*(?:B|bytes?)",s,re.I)
            if m:return str(int(m[1])),"byte_unit"
        if EQUATION.fullmatch(s) and INTEGER.fullmatch(s.rsplit("=",1)[1].strip()):
            return str(int(s.rsplit("=",1)[1].strip())),"equation_rhs"
        return MISSING,"not_integer"
    if fmt in ("csv","csv_none"):
        if fmt=="csv_none" and s.upper()=="NONE":return "NONE","scalar"
        if re.fullmatch(r"[+-]?[0-9]{1,30}(?:\s*,\s*[+-]?[0-9]{1,30})*",s):return ",".join(str(int(x)) for x in s.split(",")),"csv"
        return MISSING,"not_csv"
    if fmt=="bitstring":
        if re.fullmatch(r"[01]+",s):return s,"bitstring"
        if re.fullmatch(r"[01](?:[\s,]+[01])+",s):return re.sub(r"[\s,]","",s),"bit_separators"
        if re.fullmatch(r"[0-9]+(?:[\s,]+[0-9]+)*",s):return s,"invalid_bit_value"
        return MISSING,"not_bitstring"
    if fmt in ("hex4","octal","error_code"):
        patt={"hex4":r"(?:0[xX])?[0-9A-Fa-f]+","octal":r"(?:0[oO])?[0-7]+","error_code":r"[0-9]+"}[fmt]
        if re.fullmatch(patt,s):
            if fmt=="hex4":s=re.sub(r"^0[xX]","",s).upper()
            if fmt=="octal":s=re.sub(r"^0[oO]","",s)
            return s,"representation"
        return MISSING,"not_requested_representation"
    if fmt in ("identifier","interface","text2"):
        if len(s)>=2 and s[0] in "\"'" and s[-1]==s[0] and s[0] not in s[1:-1]:s=s[1:-1]
        patt={"identifier":r"ID-[A-Za-z0-9]+-[0-9]+","interface":r"(?i:if)[0-9]+","text2":r"[A-Za-z]{1,16}"}[fmt]
        if re.fullmatch(patt,s):return s.lower() if fmt=="interface" else s,"representation"
        if fmt=="interface" and re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}\.?",s):return s.rstrip("."),"wrong_entity"
        return MISSING,"not_requested_entity"
    return MISSING,"unsupported_format"

def result(value,method,steps=()):
    return {"status":"unresolved" if value is MISSING else "recovered","candidate":None if value is MISSING else value,"method":method,"steps":list(steps)}

def terminal_wrapper(s):
    match=re.search(r"(?m)^"+chr(96)*3+r"(?:[A-Za-z0-9_-]+)?[ \t]*\n([^\n]+)\n"+chr(96)*3+r"[ \t]*\Z",s)
    if not match:
        math_block=re.search(r"(?m)^\$\$[ \t]*\n([^\n]+)\n\$\$[ \t]*\Z",s)
        if math_block:
            b=math_block[1].strip()
            z=re.fullmatch(r"\\text\{(?i:FINAL|ANSWER):[ \t]*\}[ \t]*(.+)",b)
            prefix=s[:math_block.start()].rstrip()
            if z:return prefix+"\nFINAL: "+z[1],True
            if re.search(r"(?i)(?:answer|result|remainder|divided by [0-9]+)\s*(?:is)?\s*:\s*$",prefix):
                return prefix+"\nFINAL: "+unwrap(b),True
    if match:
        body=match[1].strip()
        prefix=s[:match.start()].rstrip()
        if LABEL.fullmatch(unwrap(body)) or not prefix or re.search(r"(?i)(?:answer|result|output|remainder)\s*:\s*(?:\*\*|__)?$",prefix):
            return prefix+"\n"+body if prefix else body,True
    return s,False

def declarations(s):
    lines=s.splitlines();out=[];inside=False
    for i,line in enumerate(lines):
        z=line.strip()
        if re.fullmatch(r"\x60{3}(?:[A-Za-z0-9_-]+)?",z):
            inside=not inside;continue
        if inside:continue
        heading=bool(HEADING.match(z)) or z.startswith(("**","__"))
        z=HEADING.sub("",z)
        z=re.sub(r"(?i)^(?:\*\*|__)((?:final(?: answer| result)?|answer|return|result|solution|output):)(?:\*\*|__)",r"\1",z)
        z=re.sub(r"(?i)^(?:\*\*|__)((?:final(?: answer| result)?|answer|return|result|solution|output))(?:\*\*|__)\s*:",r"\1:",z)
        z=unwrap(z)
        m=LABEL.fullmatch(z)
        if not m:continue
        body=m[1].strip();end=i
        if not body:
            rest=[(j,l.strip()) for j,l in enumerate(lines[i+1:],i+1) if l.strip()]
            if rest:
                end,body=rest[0]
                if re.fullmatch(r"\x60{3}(?:[A-Za-z0-9_-]+)?",body) and len(rest)>=3 and rest[2][1]=="\x60"*3:
                    end=rest[2][0];body=rest[1][1]
                if LABEL.fullmatch(unwrap(body)):continue
        out.append((i,end,body,heading and not m[1].strip()))
    return lines,out

def recover_primary(spec,reply):
    spec=public_spec(spec)
    raw=reply.get("content")
    if not isinstance(raw,str) or not raw.strip():return result(MISSING,"empty_output")
    finish=reply.get("finish_reason")
    if reply.get("tool_calls"):return result(MISSING,"tool_call")
    s=raw.strip();steps=[]
    for _ in range(5):
        old=s
        s=ROLE.sub("",s,count=1).strip()
        s=re.sub(r"^(?:</think>\s*)+","",s,flags=re.I).strip()
        m=re.match(r"(?is)^<think>.*?</think>\s*",s)
        if m:s=s[m.end():].strip()
        if s==old:break
        steps.append("strip_leading_assistant_or_thought_boundary")
    if BLOCKED.search(s) or re.search(r"</?think>",s,re.I):return result(MISSING,"special_marker_inside_response",steps)
    if not s:return result(MISSING,"no_visible_answer",steps)
    if finish not in (None,"stop","length"):return result(MISSING,"unsupported_finish",steps)
    literal=spec.get("kind")=="protocol" and spec.get("format")=="exact"
    if literal and finish!="length":
        family=spec.get("family")
        patterns={"leading_zero":r"[0-9]+","literal_case":r"[A-Za-z0-9_-]+","unicode":r"[^\s]+","tsv":r"[^\n]+(?:[\t,][^\n]+)+","csv_quoted":r"[^\n]+,[^\n]+","multiline":r"[^\n=]+=[^\n]*\n[^\n=]+=[^\n]*","xml":r"<[^>]+>[^\n]*</[^>]+>"}
        shape=patterns.get(family)
        if shape is None:return result(MISSING,"unsupported_literal_family",steps)
        if re.fullmatch(shape,s):return result(raw,"literal_response",steps)
        z=unwrap(s)
        if z!=s and re.fullmatch(shape,z):return result(z,"wrapped_literal",steps+["unwrap_literal"])
        return result(MISSING,"no_complete_literal_claim",steps)
    s,unwrapped=terminal_wrapper(s)
    if unwrapped:steps.append("terminal_fenced_answer")
    structured=(spec.get("format")=="json" or spec.get("kind")=="extraction" or spec.get("contract")=="json")
    complete_json=structured and (s.startswith(("{","[")) and s.endswith(("}","]")))
    if finish!="length" or complete_json:
        val,method=parse_value(spec,s)
        if val is not MISSING:return result(val,method,steps)
        if method=="conflicting_json_keys":return result(MISSING,method,steps)
    if spec.get("family")=="tcp-reassembly":
        s=re.sub(r"(?im)^(#{1,6}\s+)?(?:\*\*)?final (?:cumulative )?ack\s*:",r"\1FINAL:",s)
    lines,decl=declarations(s)
    if decl:
        last_nonempty=max(i for i,l in enumerate(lines) if l.strip())
        parsed=[]
        for i,j,b,heading in decl:
            if spec.get("format")=="bitstring" and j>i and all(re.fullmatch(r"[01]",l.strip()) for l in lines[j:] if l.strip()):
                j=max(k for k,l in enumerate(lines) if l.strip());b="\n".join(l.strip() for l in lines[i+1:j+1] if l.strip())
            val,method=parse_value(spec,b,True)
            if heading and val is MISSING and any(x[0]>i for x in decl):
                steps.append("ignore_section_heading_without_claim")
                continue
            parsed.append((i,j,b,val,method))
        if not parsed:return result(MISSING,"no_explicit_claim",steps)
        complete=parsed
        if finish=="length":
            if (raw.endswith("\n") or unwrapped) and all(x[3] is not MISSING for x in parsed) and len({canonical(x[3]) for x in parsed})==1:
                steps.append("complete_delimited_claim_before_length_limit")
            elif len(parsed)<3:return result(MISSING,"truncated_before_commitment",steps)
            p=parsed[-1];prior=parsed[:-1]
            if "complete_delimited_claim_before_length_limit" in steps:
                complete=parsed
            elif all(x[3] is not MISSING for x in prior) and len({canonical(x[3]) for x in prior})==1 and p[2] and all(x[2].startswith(p[2]) and x[2]!=p[2] for x in prior):
                complete=prior;steps.append("ignore_truncated_repeated_prefix")
            elif all(x[3] is not MISSING for x in parsed) and len({canonical(x[3]) for x in parsed})==1 and len(parsed)>=2:
                complete=parsed
            else:return result(MISSING,"truncated_or_conflicting_declarations",steps)
        if any(x[3] is MISSING for x in complete):
            if len({canonical(x[3]) for x in complete if x[3] is not MISSING})>1:
                return result(MISSING,"conflicting_declarations",steps)
            if any(x[4]=="conflicting_json_keys" for x in complete):
                return result(MISSING,"conflicting_json_keys",steps)
            if any(not x[2].strip() for x in complete):
                return result(MISSING,"empty_declaration",steps)
            return result(MISSING,"malformed_declaration",steps)
        if len({canonical(x[3]) for x in complete})!=1:return result(MISSING,"conflicting_declarations",steps)
        if parsed[-1][1]!=last_nonempty:return result(MISSING,"nonterminal_declaration",steps)
        if len(complete)==1 and complete[0][0]>0:
            context=next((l.strip() for l in reversed(lines[:complete[0][0]]) if l.strip()),"")
            if re.search(r"(?i)\b(?:example|illustrat(?:ion|ive)|hypothetical|do not (?:use|endorse)|not my answer|not (?:the|a) (?:final )?answer)\b",context):
                return result(MISSING,"example_or_unendorsed_declaration",steps)
        return result(complete[-1][3],"repeated_declaration" if len(complete)>1 else "explicit_declaration",steps+[complete[-1][4]])
    if finish=="length":return result(MISSING,"truncated_before_commitment",steps)
    if spec.get("kind") in ("extraction","protocol") or spec.get("contract")=="json" or spec.get("format")=="json":return result(MISSING,"no_complete_structured_claim",steps)
    nonempty=[l.strip() for l in lines if l.strip()]
    last=unwrap(nonempty[-1])
    if UNCERTAIN.search(last):return result(MISSING,"uncertain_claim",steps)
    if len(nonempty)>=2:
        normalized=[parse_value(spec,unwrap(l)) for l in nonempty]
        if all(v is not MISSING for v,_ in normalized) and len({canonical(v) for v,_ in normalized})==1:
            return result(normalized[0][0],"identical_scalar_lines",steps)
    if spec.get("format")=="text2":
        m=re.fullmatch(r"(?i)the two (?:ascii characters|characters|character string|[- ]?character string) (?:in the answer|are|is)?\s*(?:are|is)?\s*:?\s*(.+?)\.?",last)
        if m:
            pair=re.fullmatch(r"['\"]([a-z])['\"]\s+and\s+['\"]([a-z])['\"]",m[1],re.I)
            body=pair[1]+pair[2] if pair else m[1]
            val,method=parse_value(spec,body.rstrip("."),True)
            if val is not MISSING:return result(val,"explicit_text_pair",steps+[method])
    if spec.get("format")=="interface":
        m=re.fullmatch(r"(?i)(?:the )?(?:(?:selected|correct) interface(?: for the interface with the route to [0-9.]+)?|interface selected) is\s+(.+?)\.",last)
        if m:
            val,method=parse_value(spec,m[1],True)
            if val is not MISSING:return result(val,"terminal_entity_phrase",steps+[method])
    if spec.get("format")=="integer" and spec.get("family")=="ipv4-cidr-boundaries":
        m=re.fullmatch(r"(?:[0-9.]+/[0-9]+) has ([0-9]+) usable host addresses\.",last)
        if m:return result(str(int(m[1])),"explicit_host_count",steps)

    m=FINAL_PHRASE.fullmatch(last)
    if not m and spec.get("family")=="sqlite-wal-snapshots":m=READS.fullmatch(last)
    if m:
        body=m[1].rstrip(".")
        val,method=parse_value(spec,body,True)
        if val is not MISSING:return result(val,"terminal_answer_phrase",steps+[method])
    if len(nonempty)>=2:
        v,method=parse_value(spec,last,True)
        prev=nonempty[-2].rstrip(".")
        m=FINAL_PHRASE.fullmatch(unwrap(prev))
        if not m and spec.get("family")=="sqlite-wal-snapshots":m=READS.fullmatch(unwrap(prev))
        if m and v is not MISSING:
            v2,_=parse_value(spec,m[1],True)
            if v2 is not MISSING and canonical(v)==canonical(v2):return result(v,"matching_terminal_claim",steps+[method])
        prev_value,_=parse_value(spec,unwrap(prev),True)
        if v is not MISSING and prev_value is not MISSING and canonical(v)==canonical(prev_value):return result(v,"matching_terminal_claim",steps+[method])
    if len(nonempty)>=2 and re.fullmatch(r"(?i)(?:so,\s*)?(?:the\s+)?(?:answer|result|remainder|final answer|final result|requested value)\s+is\s*:",unwrap(nonempty[-2])):
        val,method=parse_value(spec,last,True)
        if val is not MISSING:return result(val,"split_answer_phrase",steps+[method])
    if len(nonempty)==1 and last.endswith("."):
        val,method=parse_value(spec,last[:-1],True)
        if val is not MISSING:return result(val,"terminal_punctuation",steps+[method])
    return result(MISSING,"no_unambiguous_final_answer",steps)

def recover(spec,reply):
    from recovery_extended import recover_extended
    spec=public_spec(spec)
    first=recover_primary(spec,reply)
    return recover_extended(spec,reply,first)


def compare(task,rec):
    if rec["status"]!="recovered":return None,None
    c=rec["candidate"];gold=task.get("answer")
    if task.get("kind")=="extraction":
        if c["decision"]=="abstain":return gold is None,None
        q=c.get("quote");source=task.get("response","")
        evidence=task.get("evidence",[])
        relevant=isinstance(q,str) and bool(q) and q in source and (q in evidence or (q in source.splitlines() and any(e in q for e in evidence)))
        return gold is not None and c["answer"]==str(gold),relevant
    if task.get("kind")=="protocol":
        return canonical(c)==canonical(gold),None
    if task.get("format")=="json":return canonical(c)==canonical(gold),None
    if task.get("format") in ("hex4","octal","error_code","interface"):
        from conceptladder.exact import normalize_exact
        a=normalize_exact(c,task["format"])
        b=normalize_exact(str(gold),task["format"])
        if a is not None and b is not None:return a==b,None
    return c==str(gold),None

UNKNOWN_METHODS={
    "empty_output":"empty_output",
    "no_visible_answer":"no_visible_answer",
    "empty_declaration":"empty_declaration",
    "conflicting_declarations":"conflicting_declarations",
    "conflicting_json_keys":"conflicting_json_keys",
    "malformed_declaration":"malformed_declaration",
    "nonterminal_declaration":"nonterminal_declaration",
    "uncertain_claim":"uncertain_claim",
    "example_or_unendorsed_declaration":"unendorsed_declaration",
    "tool_call":"tool_call",
    "special_marker_inside_response":"special_marker_blocked",
    "unsupported_finish":"unsupported_finish",
    "no_complete_structured_claim":"structured_claim_unresolved",
    "no_complete_literal_claim":"literal_claim_unresolved",
    "unsupported_literal_family":"unsupported_format",
    "conflicting_evidence_fields":"conflicting_evidence_fields",
    "missing_answer_field":"missing_answer_field",
    "malformed_structured_payload":"malformed_structured_payload",
    "literal_payload_unidentified":"literal_payload_unidentified",
    "ambiguous_malformed_declaration":"ambiguous_malformed_declaration",
    "explicit_no_answer":"explicit_no_answer",
    "descriptive_answer_not_encoded":"descriptive_answer_not_encoded",
    "instruction_echo_without_claim":"instruction_echo_without_claim",
    "invalid_answer_representation":"invalid_answer_representation",
    "wrong_structured_answer_type":"wrong_structured_answer_type",
    "repeated_question_without_answer":"repeated_question_without_answer",
    "source_echo_without_claim":"source_echo_without_claim",
    "tautological_answer":"tautological_answer",
    "answer_or_intermediate_ambiguous":"answer_or_intermediate_ambiguous",
    "multiple_or_malformed_literal_records":"multiple_or_malformed_literal_records",
    "unsupported_answer_unit":"unsupported_answer_unit",
    "placeholder_without_answer":"placeholder_without_answer",
    "unfinished_reasoning":"unfinished_reasoning",
    "conflicting_answer_directives":"conflicting_answer_directives",
    "no_explicit_claim":"unclassified_response",
    "no_unambiguous_final_answer":"unclassified_response",
}
UNKNOWN_REVIEW={"answer_or_intermediate_ambiguous","multiple_or_malformed_literal_records","unsupported_answer_unit","literal_payload_unidentified","ambiguous_malformed_declaration","malformed_structured_payload","invalid_answer_representation","malformed_declaration","structured_claim_unresolved","literal_claim_unresolved","unclassified_response","unsupported_format","unsupported_finish","nonterminal_declaration","special_marker_blocked"}

def classify_unknown(rec,reply,correct):
    finish=reply.get("finish_reason")
    termination="length" if finish=="length" else "stop" if finish=="stop" else "missing" if finish is None else "other"
    if correct is not None:
        return {"finish_reason":finish,"termination":termination,"truncated":None if finish is None else finish=="length","unknown_reason":None,"unknown_detail":None,"review_required":False}
    method=rec["method"]
    reason="truncated" if termination=="length" else UNKNOWN_METHODS.get(method,"unclassified_response")
    return {"finish_reason":finish,"termination":termination,"truncated":None if finish is None else finish=="length","unknown_reason":reason,"unknown_detail":method,"review_required":reason in UNKNOWN_REVIEW}

def assess(task,reply,prior=None):
    from failure_corpus import diagnose
    prior=prior or {};d=diagnose(task,reply,prior)
    rec=recover(public_spec(task),reply)
    if rec["status"]=="unresolved" and task.get("kind")=="extraction" and isinstance(reply.get("content"),str):
        source=task.get("response","").strip()
        visible=reply["content"].strip()
        if source and (visible==source or visible==source+"\n\n"+source):
            rec={**rec,"method":"source_echo_without_claim"}
    correct,evidence=compare(task,rec)
    legacy=prior.get("score",{});old=legacy.get("semantic_correct")
    compliant=legacy.get("format_compliant")
    joint=correct is True and compliant is True and (task.get("kind")!="extraction" or rec["candidate"]["decision"]=="abstain" or evidence is True)
    return {**rec,**classify_unknown(rec,reply,correct),"semantic_correct":correct,"evidence_supported":evidence,"format_compliant_unchanged":compliant,"joint_success_recovered":joint if compliant is not None else None,"legacy_score":legacy,"transition":("correct" if old is True else "wrong" if old is False else "unknown")+"->"+("correct" if correct is True else "wrong" if correct is False else "unknown"),"label_strategies":{f:STRATEGIES.get(f,"inspect_without_guessing") for f in d["labels"]},"labels":d["labels"],"observations":d["observations"],"evaluator_flags":d["evaluator_flags"]}

def report(rows):
    transitions=collections.Counter(r["transition"] for r in rows)
    reasons=collections.Counter()
    details=collections.Counter()
    matrix={k:{v:0 for v in ("correct","wrong","unknown")} for k in ("stop","length","missing","other")}
    unknown_by_termination={k:{} for k in matrix}
    review=0
    for r in rows:
        state="correct" if r["semantic_correct"] is True else "wrong" if r["semantic_correct"] is False else "unknown"
        termination=r["termination"]
        matrix[termination][state]+=1
        if state=="unknown":
            reason=r["unknown_reason"]
            if reason is None:raise ValueError("Unknown row without reason")
            reasons[reason]+=1
            details[r["unknown_detail"]]+=1
            bucket=unknown_by_termination[termination]
            bucket[reason]=bucket.get(reason,0)+1
            review+=int(r["review_required"])
    unknown=sum(reasons.values())
    truncated=reasons["truncated"]
    assert unknown==sum(v["unknown"] for v in matrix.values())
    assert truncated==matrix["length"]["unknown"]
    return {"attempted":len(rows),"legacy_unknown":sum(r["legacy_score"].get("semantic_correct") is None for r in rows),"recovered_correct":sum(r["semantic_correct"] is True for r in rows),"recovered_wrong":sum(r["semantic_correct"] is False for r in rows),"remaining_unknown":unknown,"unknown_truncated":truncated,"unknown_nontruncated":matrix["stop"]["unknown"]+matrix["other"]["unknown"],"unknown_finish_missing":matrix["missing"]["unknown"],"unknown_unclassified":reasons["unclassified_response"],"unknown_nontruncated_classified":sum(v for k,v in unknown_by_termination["stop"].items() if k!="unclassified_response")+sum(v for k,v in unknown_by_termination["other"].items() if k!="unclassified_response"),"unknown_breakdown":dict(sorted((k,v) for k,v in reasons.items() if v)),"unknown_details":dict(sorted(details.items())),"unknown_by_termination":unknown_by_termination,"termination_by_semantic_outcome":matrix,"unknown_review_required":review,"original_joint_success":sum(r["legacy_score"].get("joint_success") is True for r in rows),"recovered_joint_success":sum(r["joint_success_recovered"] is True for r in rows),"transitions":dict(sorted(transitions.items())),"methods":dict(collections.Counter(r["method"] for r in rows))}

def corpus_replay(path):
    from failure_corpus import records
    groups=collections.defaultdict(list);label_rows=collections.defaultdict(list);rows=[]
    for r in records(path):
        d=assess(r["task"],r["reply"],r["prior"]);d.update(id=r["id"],model=r["model"],kind=r["task"]["kind"])
        rows.append(d);groups[r["model"]].append(d)
        for f in d["labels"]:label_rows[f].append(d)
    return {"version":VERSION,"overall":report(rows),"by_model":{k:report(v) for k,v in groups.items()},"by_label":{k:{"strategy":STRATEGIES.get(k,"inspect_without_guessing"),**report(v)} for k,v in label_rows.items()},"rows":rows}

def run_replay(run):
    import measurement
    measurement.score(run)
    from failure_corpus import diagnose_run
    diag=diagnose_run(run)
    lookup={(x["id"],x["mode"],x["budget"]):x for x in diag["rows"]}
    tasks={t["id"]:t for t in run["manifest"]["tasks"]};rows=[];groups=collections.defaultdict(list);errors=0
    for r in run["rows"]:
        if "error" in r:errors+=1;continue
        k=(r["id"],r["mode"],r["budget"]);d=lookup[k];t={**tasks[r["id"]],"kind":"reasoning","mode":r["mode"],"budget":r["budget"]};ch=r["raw"]["choices"][0]
        reply={**ch["message"],"finish_reason":ch.get("finish_reason"),"completion_tokens":(r["raw"].get("usage") or {}).get("completion_tokens")}
        rec=dict(d["recovery"]);rec.update(id=r["id"],track=t["track"],mode=r["mode"],budget=r["budget"])
        rows.append(rec);groups[(t["track"],r["mode"],r["budget"])].append(rec)
    planned=len(tasks)*len(run["modes"])*len(run["budgets"])
    return {"version":VERSION,"model":run["model"],"planned":planned,"transport_errors":errors,"not_run":planned-len(run["rows"]),"overall":report(rows),"profiles":[{"track":k[0],"mode":k[1],"budget":k[2],**report(v)} for k,v in groups.items()],"rows":rows}

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["corpus","run"]);p.add_argument("input");p.add_argument("--out",required=True)
    a=p.parse_args();out=corpus_replay(a.input) if a.mode=="corpus" else run_replay(json.loads(Path(a.input).read_text()))
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps(out["overall"],indent=2))
if __name__=="__main__":main()
