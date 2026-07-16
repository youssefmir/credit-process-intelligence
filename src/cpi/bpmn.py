"""Génération des modèles BPMN 2.0 AS-IS et TO-BE (avec diagramme et couloirs).

Les modèles sont décrits de façon déclarative (nœuds placés sur une grille couloir ×
colonne, flux avec indication de tracé) puis sérialisés en BPMN 2.0 standard, lisible par
bpmn-js, Camunda Modeler ou tout outil conforme. Les annotations reprennent les chiffres
mesurés par le pipeline (aucune saisie manuelle).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from cpi.config import DOCS_DIR, SITE_BPMN_DIR

LANE_H = 250
POOL_LABEL = 30
LANE_LABEL = 30
COL_W = 170
X0 = POOL_LABEL + LANE_LABEL + 90
CLIENT_H = 70
GAP = 30  # entre la piscine client et la piscine de l'établissement
ROWS = (88, 180)  # centres des rangées dans un couloir (relatifs au haut du couloir)
TOP_ROW = 22  # rangée haute (événements de boucle au-dessus de la rangée principale)

SIZES = {
    "task": (130, 76),
    "userTask": (130, 76),
    "serviceTask": (130, 76),
    "sendTask": (130, 76),
    "exclusiveGateway": (50, 50),
    "eventBasedGateway": (50, 50),
    "startEvent": (36, 36),
    "endEvent": (36, 36),
    "intermediateCatchEvent": (36, 36),
}

INK = "#111111"
STYLE = {
    "loop": ("#9A6B00", "#FFF1C2"),
    "ai": ("#0B3D91", "#E7EDF8"),
    "ok": ("#00843D", "#E3F3EA"),
    "cancel": ("#D62828", "#FBE6E6"),
    "decline": ("#6C757D", "#EEF0F2"),
}


@dataclass
class Node:
    id: str
    kind: str
    name: str
    lane: str
    col: float
    row: int | str = 0  # 0, 1 ou "top"
    event: str | None = None  # message | timer
    style: str | None = None
    loop: bool = False

    def size(self) -> tuple[int, int]:
        return SIZES[self.kind]


@dataclass
class Flow:
    id: str
    source: str
    target: str
    name: str | None = None
    route: str = "h"  # h | down | up | under | over | left-down | points
    points: list[tuple[float, float]] | None = None


@dataclass
class Annotation:
    id: str
    text: str
    target: str
    dx: float
    dy: float
    width: int = 190
    height: int = 64


@dataclass
class Model:
    key: str
    name: str
    lanes: list[tuple[str, str]]
    nodes: list[Node]
    flows: list[Flow]
    messages: list[tuple[str, str, str, str]]  # id, source, target, name
    annotations: list[Annotation] = field(default_factory=list)
    columns: int = 13


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %".replace(".", ",")


def _num(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


# --- Modèles -----------------------------------------------------------------------


def build(s: dict[str, Any], tobe: bool) -> Model:
    """AS-IS (observé) ou TO-BE (cible) ; le TO-BE insère trois tâches outillées par l'IA."""
    d = 1 if tobe else 0  # décalage après le contrôle de complétude
    e = 2 if tobe else 0  # décalage après le calcul du risque d'abandon
    f = 3 if tobe else 0  # décalage après la fiche de pré-analyse
    lanes = [
        ("L_sys", "Système (règles automatiques)"),
        ("L_contact", "Centre de contact"),
        ("L_back", "Back-office validation"),
    ]
    complete_name = (
        "Compléter les seuls manques restants" if tobe else "Compléter la demande par téléphone"
    )
    nodes = [
        Node("Start", "startEvent", "Demande déposée", "L_sys", 0, event="message"),
        Node("T_precheck", "serviceTask", "Pré-contrôler la demande", "L_sys", 1),
        Node("G_eligible", "exclusiveGateway", "Éligible ?", "L_sys", 2),
        Node(
            "E_declined_auto",
            "endEvent",
            "Refusée au pré-contrôle",
            "L_sys",
            2,
            row=1,
            style="decline",
        ),
        Node("T_complete", "userTask", complete_name, "L_contact", 3 + d),
        Node("G_complete", "exclusiveGateway", "Demande complète ?", "L_contact", 4 + d),
        Node(
            "E_cancel_completion",
            "endEvent",
            "Annulée en complétion",
            "L_contact",
            4 + d,
            row=1,
            style="cancel",
        ),
        Node("T_offer", "userTask", "Préparer et envoyer l'offre", "L_contact", 5 + d),
        Node("G_wait", "eventBasedGateway", "", "L_contact", 6 + e),
        Node(
            "E_new_offer",
            "intermediateCatchEvent",
            "Nouvelle offre demandée",
            "L_contact",
            6 + e,
            row="top",
            event="message",
            style="loop",
        ),
        Node(
            "E_back",
            "intermediateCatchEvent",
            "Offre signée reçue",
            "L_contact",
            7 + e,
            event="message",
        ),
        Node(
            "E_timer",
            "intermediateCatchEvent",
            "Pas de retour à la date prévue",
            "L_contact",
            7 + e,
            row=1,
            event="timer",
        ),
        Node(
            "T_followup",
            "userTask",
            "Relancer selon la priorité" if tobe else "Relancer le client",
            "L_contact",
            8 + e,
            row=1,
            style="loop",
            loop=True,
        ),
        Node(
            "G_expired", "exclusiveGateway", "Offre expirée (30 jours) ?", "L_contact", 9 + e, row=1
        ),
        Node(
            "E_cancel_expired",
            "endEvent",
            "Annulée faute de retour",
            "L_contact",
            10 + e,
            row=1,
            style="cancel",
        ),
        Node(
            "T_validate",
            "userTask",
            "Valider le dossier (décision humaine)" if tobe else "Valider le dossier",
            "L_back",
            8 + f,
        ),
        Node("G_docs", "exclusiveGateway", "Dossier complet ?", "L_back", 9 + f),
        Node(
            "T_missing",
            "userTask",
            "Relancer pour pièces manquantes",
            "L_back",
            9 + f,
            row=1,
            style="loop",
            loop=True,
        ),
        Node(
            "E_docs",
            "intermediateCatchEvent",
            "Pièces reçues",
            "L_back",
            8 + f,
            row=1,
            event="message",
            style="loop",
        ),
        Node("G_decision", "exclusiveGateway", "Décision", "L_back", 10 + f),
        Node("T_activate", "serviceTask", "Enregistrer et activer le prêt", "L_back", 11 + f),
        Node("E_activated", "endEvent", "Prêt activé", "L_back", 12 + f, style="ok"),
        Node(
            "E_declined",
            "endEvent",
            "Refusée après examen",
            "L_back",
            11 + f,
            row=1,
            style="decline",
        ),
    ]
    flows = [
        Flow("F01", "Start", "T_precheck"),
        Flow("F02", "T_precheck", "G_eligible"),
        Flow("F03", "G_eligible", "E_declined_auto", "non", route="down"),
        Flow("F05", "T_complete", "G_complete"),
        Flow("F06", "G_complete", "E_cancel_completion", "abandon", route="down"),
        Flow("F07", "G_complete", "T_offer", "oui"),
        Flow("F09", "G_wait", "E_back"),
        Flow("F10", "G_wait", "E_timer", route="down"),
        Flow("F11", "G_wait", "E_new_offer", route="up"),
        Flow("F12", "E_new_offer", "T_offer", route="left-down"),
        Flow("F13", "E_timer", "T_followup"),
        Flow("F14", "T_followup", "G_expired"),
        Flow("F15", "G_expired", "E_cancel_expired", "oui"),
        Flow("F16", "G_expired", "G_wait", "non", route="under"),
        Flow("F18", "T_validate", "G_docs"),
        Flow("F19", "G_docs", "T_missing", "non", route="down"),
        Flow("F20", "T_missing", "E_docs"),
        Flow("F21", "E_docs", "T_validate", route="up"),
        Flow("F22", "G_docs", "G_decision", "oui"),
        Flow("F23", "G_decision", "T_activate", "accord"),
        Flow("F24", "T_activate", "E_activated"),
        Flow("F25", "G_decision", "E_declined", "refus", route="down"),
    ]
    if tobe:
        nodes += [
            Node(
                "T_ai_check",
                "serviceTask",
                "Contrôler la complétude et lire les pièces (IA)",
                "L_sys",
                3,
                style="ai",
            ),
            Node(
                "T_ai_score",
                "serviceTask",
                "Calculer le risque d'abandon (pilote)",
                "L_contact",
                7,
                style="ai",
            ),
            Node(
                "T_ai_brief",
                "serviceTask",
                "Préparer la fiche de pré-analyse (IA)",
                "L_back",
                10,
                style="ai",
            ),
        ]
        flows += [
            Flow("F04a", "G_eligible", "T_ai_check", "oui"),
            Flow("F04b", "T_ai_check", "T_complete"),
            Flow("F08a", "T_offer", "T_ai_score"),
            Flow("F08b", "T_ai_score", "G_wait"),
            Flow("F17a", "E_back", "T_ai_brief"),
            Flow("F17b", "T_ai_brief", "T_validate"),
        ]
    else:
        flows += [
            Flow("F04", "G_eligible", "T_complete", "oui"),
            Flow("F08", "T_offer", "G_wait"),
            Flow("F17", "E_back", "T_validate"),
        ]
    messages = [
        ("M1", "P_client", "Start", "Demande en ligne"),
        ("M2", "T_offer", "P_client", "Offre"),
        ("M3", "P_client", "E_back", "Offre signée et justificatifs"),
    ]
    inc = s.get("incomplete_share_of_validated", 0.0)
    annotations = [
        Annotation(
            "A1",
            f"{_pct(s.get('declined_share', 0))} des demandes refusées, le plus "
            "souvent en moins d'une heure",
            "E_declined_auto",
            70,
            -6,
        ),
        Annotation(
            "A3",
            f"{_pct(s.get('cancel_rate_after_offer', 0))} des offres envoyées "
            f"finissent annulées, dont {_pct(s.get('expiry_window_share', 0))} à "
            "l'expiration des 30 jours",
            "E_cancel_expired",
            36,
            -96,
            width=220,
            height=70,
        ),
        Annotation(
            "A4",
            f"Boucle « dossier incomplet » : {_pct(inc)} des dossiers validés",
            "E_docs",
            -270,
            -28,
            width=190,
            height=56,
        ),
    ]
    if tobe:
        annotations += [
            Annotation(
                "B1",
                "Pièces vérifiées dès le dépôt : moins de boucles « incomplet » "
                "et d'appels de complétion (hypothèses chiffrées)",
                "T_ai_check",
                110,
                -40,
                width=230,
                height=70,
            ),
            Annotation(
                "B2",
                "Pilote A/B d'abord : le score actuel (ROC-AUC "
                f"{_num(s.get('model_roc_auc', 0), 2)}) ne passe pas les seuils",
                "T_ai_score",
                -30,
                -150,
                width=210,
                height=64,
            ),
            Annotation(
                "B3",
                "Aucune décision automatisée : l'analyste relit la fiche, la corrige et décide",
                "T_ai_brief",
                -500,
                62,
                width=220,
                height=60,
            ),
        ]
    else:
        annotations.append(
            Annotation(
                "A5",
                f"Seuls {_pct(s.get('first_time_right_share', 0))} des prêts "
                "approuvés suivent le chemin nominal sans reprise",
                "E_activated",
                40,
                44,
                width=200,
                height=64,
            )
        )
    title = (
        "TO-BE — processus cible avec trois apports de l'IA"
        if tobe
        else "AS-IS — processus observé (BPI Challenge 2012)"
    )
    return Model(
        "to-be" if tobe else "as-is",
        title,
        lanes,
        nodes,
        flows,
        messages,
        annotations,
        columns=14 + f,
    )


def as_is(s: dict[str, Any]) -> Model:
    return build(s, tobe=False)


def to_be(s: dict[str, Any]) -> Model:
    return build(s, tobe=True)


# --- Mise en page -------------------------------------------------------------------


def layout(model: Model) -> tuple[dict[str, Box], dict[str, Box], Box, Box]:
    lane_y = {}
    y = CLIENT_H + GAP
    for lane_id, _ in model.lanes:
        lane_y[lane_id] = y
        y += LANE_H
    width = X0 + model.columns * COL_W + 20
    pool = Box(0, CLIENT_H + GAP, width, LANE_H * len(model.lanes))
    client = Box(0, 0, width, CLIENT_H)
    lanes = {
        lane_id: Box(POOL_LABEL, lane_y[lane_id], width - POOL_LABEL, LANE_H)
        for lane_id, _ in model.lanes
    }
    boxes: dict[str, Box] = {}
    for n in model.nodes:
        w, h = n.size()
        cx = X0 + n.col * COL_W
        cy = lane_y[n.lane] + (TOP_ROW + h / 2 if n.row == "top" else ROWS[int(n.row)])
        boxes[n.id] = Box(cx - w / 2, cy - h / 2, w, h)
    return boxes, lanes, pool, client


def _anchor(kind: str, b: Box, toward: tuple[float, float]) -> tuple[float, float]:
    """Point du contour de l'élément en direction de ``toward`` : départ d'une association.

    Partir du centre ferait traverser le libellé de la tâche par le pointillé.
    """
    dx, dy = toward[0] - b.cx, toward[1] - b.cy
    if dx == 0 and dy == 0:
        return (b.cx, b.cy)
    if kind.endswith("Event"):  # cercle
        n = math.hypot(dx, dy)
        return (b.cx + b.w / 2 * dx / n, b.cy + b.w / 2 * dy / n)
    if kind.endswith("Gateway"):  # losange
        s = (b.w / 2) / (abs(dx) + abs(dy))
        return (b.cx + s * dx, b.cy + s * dy)
    sx = (b.w / 2) / abs(dx) if dx else math.inf
    sy = (b.h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return (b.cx + s * dx, b.cy + s * dy)


def route(f: Flow, a: Box, b: Box) -> list[tuple[float, float]]:
    if f.points:
        return f.points
    if f.route == "down":
        if abs(a.cx - b.cx) < 1:
            return [(a.cx, a.bottom), (b.cx, b.y)]
        if b.cx > a.cx:
            return [(a.cx, a.bottom), (a.cx, b.cy), (b.x, b.cy)]
        return [(a.cx, a.bottom), (a.cx, b.cy), (b.right, b.cy)]
    if f.route == "up":
        if abs(a.cx - b.cx) < 1:
            return [(a.cx, a.y), (b.cx, b.bottom)]
        if b.cx > a.cx:
            return [(a.cx, a.y), (a.cx, b.cy), (b.x, b.cy)]
        return [(a.cx, a.y), (a.cx, b.cy), (b.right, b.cy)]
    if f.route == "under":
        y = max(a.bottom, b.bottom) + 36
        return [(a.cx, a.bottom), (a.cx, y), (b.cx, y), (b.cx, b.bottom)]
    if f.route == "left-down":
        return [(a.x, a.cy), (b.cx, a.cy), (b.cx, b.y)]
    if f.route == "over":
        y = min(a.y, b.y) - 16
        return [(a.cx, a.y), (a.cx, y), (b.cx, y), (b.cx, b.y)]
    if abs(a.cy - b.cy) < 1:
        if b.cx < a.cx:  # retour vers la gauche sur la même rangée
            return [(a.x, a.cy), (b.right, b.cy)]
        return [(a.right, a.cy), (b.x, b.cy)]
    xm = (a.right + b.x) / 2
    return [(a.right, a.cy), (xm, a.cy), (xm, b.cy), (b.x, b.cy)]


# --- Sérialisation ------------------------------------------------------------------


def _attr(text: str) -> str:
    return escape(text, {'"': "&quot;"})


def _color(style: str | None) -> str:
    if not style:
        return ""
    stroke, fill = STYLE[style]
    return (
        f' bioc:stroke="{stroke}" bioc:fill="{fill}"'
        f' color:border-color="{stroke}" color:background-color="{fill}"'
    )


def to_xml(model: Model) -> str:
    boxes, lanes, pool, client = layout(model)
    incoming: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for f in model.flows:
        outgoing.setdefault(f.source, []).append(f.id)
        incoming.setdefault(f.target, []).append(f.id)

    proc: list[str] = []
    for lane_id, lane_name in model.lanes:
        refs = "".join(
            f"<bpmn:flowNodeRef>{n.id}</bpmn:flowNodeRef>" for n in model.nodes if n.lane == lane_id
        )
        proc.append(f'<bpmn:lane id="{lane_id}" name="{_attr(lane_name)}">{refs}</bpmn:lane>')
    lane_set = '<bpmn:laneSet id="LaneSet_1">' + "".join(proc) + "</bpmn:laneSet>"
    elements: list[str] = [lane_set]
    for n in model.nodes:
        inner = "".join(f"<bpmn:incoming>{i}</bpmn:incoming>" for i in incoming.get(n.id, []))
        inner += "".join(f"<bpmn:outgoing>{o}</bpmn:outgoing>" for o in outgoing.get(n.id, []))
        if n.loop:
            inner += "<bpmn:standardLoopCharacteristics />"
        if n.event == "message":
            inner += f'<bpmn:messageEventDefinition id="{n.id}_med" />'
        elif n.event == "timer":
            inner += f'<bpmn:timerEventDefinition id="{n.id}_ted" />'
        elements.append(
            f'<bpmn:{n.kind} id="{n.id}" name="{_attr(n.name)}">{inner}</bpmn:{n.kind}>'
        )
    for f in model.flows:
        name = f' name="{_attr(f.name)}"' if f.name else ""
        elements.append(
            f'<bpmn:sequenceFlow id="{f.id}"{name} sourceRef="{f.source}" targetRef="{f.target}" />'
        )
    for a in model.annotations:
        elements.append(
            f'<bpmn:textAnnotation id="{a.id}"><bpmn:text>{escape(a.text)}</bpmn:text>'
            f"</bpmn:textAnnotation>"
        )
        elements.append(
            f'<bpmn:association id="{a.id}_assoc" sourceRef="{a.target}" targetRef="{a.id}" />'
        )

    msg_xml = "".join(
        f'<bpmn:messageFlow id="{mid}" name="{_attr(name)}" sourceRef="{src}" targetRef="{tgt}" />'
        for mid, src, tgt, name in model.messages
    )
    collab = (
        '<bpmn:collaboration id="Collaboration_1">'
        '<bpmn:participant id="P_client" name="Client" />'
        '<bpmn:participant id="P_bank" name="Établissement de crédit à la consommation" '
        'processRef="Process_1" />'
        f"{msg_xml}</bpmn:collaboration>"
    )

    di: list[str] = []
    di.append(_shape("P_client_di", "P_client", client, extra=' isHorizontal="true"'))
    di.append(_shape("P_bank_di", "P_bank", pool, extra=' isHorizontal="true"'))
    for lane_id, box in lanes.items():
        di.append(_shape(f"{lane_id}_di", lane_id, box, extra=' isHorizontal="true"'))
    for n in model.nodes:
        b = boxes[n.id]
        extra = ' isMarkerVisible="true"' if n.kind == "exclusiveGateway" else ""
        label = ""
        if n.kind.endswith("Event") or n.kind.endswith("Gateway"):
            lw = 110
            # Étiquette au-dessus quand un flux part vers le bas (évite les chevauchements).
            leaves_down = any(
                f.source == n.id and f.route in ("down", "under") for f in model.flows
            )
            ly = (
                b.y - 34
                if n.row == "top" or (leaves_down and "Gateway" in n.kind)
                else b.bottom + 6
            )
            label = (
                f'<bpmndi:BPMNLabel><dc:Bounds x="{b.cx - lw / 2:.0f}" y="{ly:.0f}" '
                f'width="{lw}" height="27" /></bpmndi:BPMNLabel>'
            )
        di.append(_shape(f"{n.id}_di", n.id, b, extra=extra + _color(n.style), label=label))
    for f in model.flows:
        pts = route(f, boxes[f.source], boxes[f.target])
        label = ""
        if f.name:
            (x0, y0), (x1, _y1) = pts[0], pts[1]
            if abs(x0 - x1) < 1:  # premier segment vertical : étiquette à droite du trait
                lx, ly = x0 + 6, y0 + (4 if _y1 > y0 else -18)
            else:  # premier segment horizontal : étiquette au-dessus du trait
                lx, ly = x0 + 8, y0 - 18
            label = (
                f'<bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" '
                'width="50" height="14" /></bpmndi:BPMNLabel>'
            )
        di.append(_edge(f"{f.id}_di", f.id, pts, label))
    for mid, src, tgt, _ in model.messages:
        if src == "P_client":
            b = boxes[tgt]
            pts = [(b.cx, client.bottom), (b.cx, b.y)]
        else:
            b = boxes[src]
            pts = [(b.cx + 20, b.y), (b.cx + 20, client.bottom)]
        di.append(_edge(f"{mid}_di", mid, pts, ""))
    kinds = {n.id: n.kind for n in model.nodes}
    for a in model.annotations:
        t = boxes[a.target]
        box = Box(t.cx + a.dx, t.cy + a.dy, a.width, a.height)
        di.append(_shape(f"{a.id}_di", a.id, box))
        if box.y >= t.bottom:
            end = (box.x + min(30.0, box.w / 2), box.y)
        elif box.bottom <= t.y:
            end = (box.x + min(30.0, box.w / 2), box.bottom)
        elif box.x >= t.cx:
            end = (box.x, box.cy)
        else:
            end = (box.right, box.cy)
        start = _anchor(kinds[a.target], t, end)
        di.append(_edge(f"{a.id}_assoc_di", f"{a.id}_assoc", [start, end], ""))

    body = "".join(elements)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
        'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
        'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
        'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
        'xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" '
        'xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0" '
        f'id="Definitions_{model.key}" targetNamespace="https://github.com/youssefmir/'
        'credit-process-intelligence" exporter="credit-process-intelligence" '
        'exporterVersion="1.0">\n'
        f"{collab}\n"
        f'<bpmn:process id="Process_1" name="{_attr(model.name)}" isExecutable="false">'
        f"{body}</bpmn:process>\n"
        '<bpmndi:BPMNDiagram id="Diagram_1"><bpmndi:BPMNPlane id="Plane_1" '
        f'bpmnElement="Collaboration_1">{"".join(di)}</bpmndi:BPMNPlane></bpmndi:BPMNDiagram>\n'
        "</bpmn:definitions>\n"
    )


def _shape(di_id: str, ref: str, b: Box, extra: str = "", label: str = "") -> str:
    return (
        f'<bpmndi:BPMNShape id="{di_id}" bpmnElement="{ref}"{extra}>'
        f'<dc:Bounds x="{b.x:.0f}" y="{b.y:.0f}" width="{b.w:.0f}" height="{b.h:.0f}" />'
        f"{label}</bpmndi:BPMNShape>"
    )


def _edge(di_id: str, ref: str, pts: list[tuple[float, float]], label: str) -> str:
    wps = "".join(f'<di:waypoint x="{x:.0f}" y="{y:.0f}" />' for x, y in pts)
    return f'<bpmndi:BPMNEdge id="{di_id}" bpmnElement="{ref}">{wps}{label}</bpmndi:BPMNEdge>'


def write_models(summary: dict[str, Any]) -> list[Path]:
    out = []
    for model in (as_is(summary), to_be(summary)):
        xml = to_xml(model)
        for folder in (DOCS_DIR / "bpmn", SITE_BPMN_DIR):
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{model.key}.bpmn"
            path.write_text(xml, encoding="utf-8")
            out.append(path)
    return out
