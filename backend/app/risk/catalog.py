"""Fixed catalog of FIDIC/construction-contract red-flag categories to check
for. Each rule's `query_ar` is embedded and used to retrieve the clauses most
likely to discuss that topic (same multilingual e5 retrieval as QA); the LLM
then only confirms or denies the risk against those specific clauses - it
never sees the whole contract at once.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskRule:
    rule_key: str
    query_ar: str
    description_ar: str
    severity: str  # "high" | "medium" | "low"


RISK_CATALOG: list[RiskRule] = [
    RiskRule(
        rule_key="unlimited_liability",
        query_ar="حد المسؤولية والتعويض عن الأضرار",
        description_ar="عدم وجود حد أعلى لمسؤولية المتعاقد عن التعويضات (Limitation of Liability)، مما يعرّضه لمسؤولية غير محدودة.",
        severity="high",
    ),
    RiskRule(
        rule_key="uncapped_liquidated_damages",
        query_ar="غرامات التأخير اليومية وحدها الأعلى",
        description_ar="غرامات التأخير (Liquidated Damages) غير محددة بحد أعلى أو نسبة قصوى من قيمة العقد.",
        severity="high",
    ),
    RiskRule(
        rule_key="unilateral_termination",
        query_ar="حق إنهاء العقد وفسخه",
        description_ar="حق فسخ أو إنهاء العقد ممنوح لجهة واحدة فقط (الجهة المالكة) دون حق متكافئ للمتعاقد أو دون تعويض عادل.",
        severity="high",
    ),
    RiskRule(
        rule_key="narrow_force_majeure",
        query_ar="تعريف القوة القاهرة Force Majeure",
        description_ar="تعريف القوة القاهرة ضيق جداً أو يستثني أحداثاً معتادة (كالأوبئة أو التأخر الحكومي)، مما يحرم المتعاقد من حماية معقولة.",
        severity="medium",
    ),
    RiskRule(
        rule_key="no_extension_of_time",
        query_ar="تمديد مدة التنفيذ Extension of Time",
        description_ar="غياب آلية واضحة لتمديد مدة التنفيذ عند تأخر الجهة المالكة أو وقوع أحداث خارجة عن إرادة المتعاقد.",
        severity="medium",
    ),
    RiskRule(
        rule_key="unilateral_variation",
        query_ar="حق التغيير في نطاق العمل Variations",
        description_ar="حق إصدار تغييرات (Variations) في نطاق العمل ممنوح للجهة المالكة من طرف واحد دون آلية تعويض عادل عن التكلفة والوقت.",
        severity="medium",
    ),
    RiskRule(
        rule_key="excessive_retention",
        query_ar="نسبة ضمان الاحتجاز Retention Money",
        description_ar="نسبة ضمان الاحتجاز (Retention) مرتفعة جداً أو بدون آلية واضحة لإعادتها بعد انتهاء فترة الصيانة.",
        severity="medium",
    ),
    RiskRule(
        rule_key="unfavorable_payment_terms",
        query_ar="مواعيد ومهل سداد المستخلصات",
        description_ar="مهلة سداد المستخلصات طويلة جداً أو غير مرتبطة بآجال محددة وواضحة، مما يعرّض المتعاقد لمخاطر تدفق نقدي.",
        severity="medium",
    ),
    RiskRule(
        rule_key="one_sided_indemnification",
        query_ar="التعويض وإخلاء المسؤولية Indemnification",
        description_ar="بنود التعويض (Indemnification) أحادية الجانب تُلزم المتعاقد بتعويض الجهة المالكة دون التزام مماثل بالعكس.",
        severity="medium",
    ),
    RiskRule(
        rule_key="no_dispute_resolution",
        query_ar="آلية تسوية النزاعات Dispute Resolution",
        description_ar="غياب آلية واضحة لتسوية النزاعات (تحكيم أو قضاء) أو نص يحرم المتعاقد من حق التحكيم.",
        severity="high",
    ),
]
