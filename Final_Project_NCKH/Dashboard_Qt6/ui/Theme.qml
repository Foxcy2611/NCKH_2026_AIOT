import QtQuick

QtObject {
    property bool dark: true

    readonly property color page:
        dark ? "#0A0F1D" : "#F5F7FB"

    readonly property color sidebar:
        dark ? "#0D1424" : "#FFFFFF"

    readonly property color surface:
        dark ? "#111A2C" : "#FFFFFF"

    readonly property color surface2:
        dark ? "#151F33" : "#F8FAFD"

    readonly property color hover:
        dark ? "#18243A" : "#F0F5FC"

    readonly property color selected:
        dark ? "#16294A" : "#EAF2FF"

    readonly property color border:
        dark ? "#202D44" : "#DFE6F0"

    readonly property color text:
        dark ? "#F4F7FC" : "#172033"

    readonly property color text2:
        dark ? "#9CAAC0" : "#64748B"

    readonly property color text3:
        dark ? "#66758D" : "#94A3B8"

    readonly property color blue: "#4A8DFF"
    readonly property color cyan: "#23C8D7"
    readonly property color green: "#35C988"
    readonly property color amber: "#F5B84B"
    readonly property color red: "#F16675"
    readonly property color purple: "#A78BFA"

    readonly property color blueSoft:
        dark ? "#19325A" : "#EAF2FF"

    readonly property color greenSoft:
        dark ? "#173B35" : "#E9F9F3"

    readonly property color amberSoft:
        dark ? "#40321A" : "#FFF5DF"

    readonly property color redSoft:
        dark ? "#41232B" : "#FFF0F2"
}
