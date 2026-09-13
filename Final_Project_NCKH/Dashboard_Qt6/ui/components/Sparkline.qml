import QtQuick

Canvas {
    id: root

    property var values: []
    property color lineColor: "#4A8DFF"

    onValuesChanged: requestPaint()
    onLineColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)

        if (!values || values.length < 2)
            return

        var minV = values[0]
        var maxV = values[0]

        for (var i = 1; i < values.length; ++i) {
            minV = Math.min(minV, values[i])
            maxV = Math.max(maxV, values[i])
        }

        if (maxV === minV)
            maxV = minV + 1

        var pad = 2
        var usableW = width - pad * 2
        var usableH = height - pad * 2

        ctx.beginPath()
        ctx.lineWidth = 2
        ctx.strokeStyle = lineColor

        for (var j = 0; j < values.length; ++j) {
            var x = pad + (j / (values.length - 1)) * usableW
            var y = pad + (1 - (values[j] - minV) / (maxV - minV)) * usableH

            if (j === 0)
                ctx.moveTo(x, y)
            else
                ctx.lineTo(x, y)
        }

        ctx.stroke()
    }
}
