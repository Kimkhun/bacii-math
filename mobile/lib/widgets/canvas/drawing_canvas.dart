import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../../models/stroke_doc.dart';
import '../../core/theme/app_theme.dart';

enum CanvasTool { pen, eraser, ruler }

class DrawingCanvasController extends ChangeNotifier {
  List<CanvasStroke> _strokes = [];
  final List<List<CanvasStroke>> _undoStack = [];
  final List<List<CanvasStroke>> _redoStack = [];

  CanvasTool _currentTool = CanvasTool.pen;
  double _penWidth = 2.5;
  double _eraserWidth = 20.0;
  bool _hasPenActive = false; // For palm rejection

  List<CanvasStroke> get strokes => List.unmodifiable(_strokes);
  CanvasTool get currentTool => _currentTool;
  double get penWidth => _penWidth;
  double get eraserWidth => _eraserWidth;
  bool get canUndo => _undoStack.isNotEmpty;
  bool get canRedo => _redoStack.isNotEmpty;
  bool get hasInk => _strokes.isNotEmpty;

  void setTool(CanvasTool tool) {
    _currentTool = tool;
    notifyListeners();
  }

  void setPenWidth(double width) {
    _penWidth = width;
    notifyListeners();
  }

  void setEraserWidth(double width) {
    _eraserWidth = width;
    notifyListeners();
  }

  void startStroke(CanvasPoint point, {String? pointerType}) {
    if (pointerType == 'pen') {
      _hasPenActive = true;
    }
    _saveUndoState();

    final toolName = _currentTool == CanvasTool.eraser ? 'eraser' : (_currentTool == CanvasTool.ruler ? 'ruler' : 'pen');
    final strokeWidth = _currentTool == CanvasTool.eraser ? _eraserWidth : _penWidth;

    _strokes.add(CanvasStroke(
      kind: _currentTool == CanvasTool.ruler ? 'line' : 'path',
      points: [point],
      tool: toolName,
      width: strokeWidth,
      pointerType: pointerType,
    ));
    _redoStack.clear();
    notifyListeners();
  }

  void appendPoint(CanvasPoint point, {String? pointerType}) {
    // Palm rejection: if a pen is in use, ignore touch inputs
    if (_hasPenActive && pointerType == 'touch') {
      return;
    }

    if (_strokes.isEmpty) return;
    final lastStroke = _strokes.last;

    if (lastStroke.kind == 'line') {
      // Ruler line: update end point
      if (lastStroke.points.length < 2) {
        lastStroke.points.add(point);
      } else {
        lastStroke.points[1] = point;
      }
    } else {
      // Freehand path
      lastStroke.points.add(point);
    }
    notifyListeners();
  }

  void endStroke() {
    notifyListeners();
  }

  void _saveUndoState() {
    _undoStack.add(List<CanvasStroke>.from(_strokes.map((s) => CanvasStroke(
          kind: s.kind,
          points: List<CanvasPoint>.from(s.points),
          tool: s.tool,
          width: s.width,
          pointerType: s.pointerType,
        ))));
  }

  void undo() {
    if (!canUndo) return;
    _redoStack.add(List<CanvasStroke>.from(_strokes));
    _strokes = _undoStack.removeLast();
    notifyListeners();
  }

  void redo() {
    if (!canRedo) return;
    _saveUndoState();
    _strokes = _redoStack.removeLast();
    notifyListeners();
  }

  void clear() {
    if (_strokes.isEmpty) return;
    _saveUndoState();
    _strokes.clear();
    _redoStack.clear();
    _hasPenActive = false;
    notifyListeners();
  }

  void loadStrokes(StrokeDocument doc) {
    _strokes = List<CanvasStroke>.from(doc.strokes);
    _undoStack.clear();
    _redoStack.clear();
    notifyListeners();
  }

  StrokeDocument toStrokeDocument() {
    return StrokeDocument(strokes: _strokes);
  }
}

class DrawingCanvas extends StatefulWidget {
  final DrawingCanvasController controller;
  final double height;
  final bool showGrid;

  const DrawingCanvas({
    super.key,
    required this.controller,
    this.height = 340,
    this.showGrid = true,
  });

  @override
  State<DrawingCanvas> createState() => _DrawingCanvasState();
}

class _DrawingCanvasState extends State<DrawingCanvas> {
  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onCanvasUpdated);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onCanvasUpdated);
    super.dispose();
  }

  void _onCanvasUpdated() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = widget.controller;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.slate300),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Canvas Toolbar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: const BoxDecoration(
              color: AppTheme.slate100,
              border: Border(bottom: BorderSide(color: AppTheme.slate200)),
            ),
            child: Row(
              children: [
                // Pen Tool
                _ToolButton(
                  icon: Icons.edit_rounded,
                  label: 'Pen',
                  isSelected: ctrl.currentTool == CanvasTool.pen,
                  onTap: () => ctrl.setTool(CanvasTool.pen),
                ),
                const SizedBox(width: 4),
                // Eraser Tool
                _ToolButton(
                  icon: Icons.auto_fix_normal_rounded,
                  label: 'Eraser',
                  isSelected: ctrl.currentTool == CanvasTool.eraser,
                  onTap: () => ctrl.setTool(CanvasTool.eraser),
                ),
                const SizedBox(width: 4),
                // Ruler Tool
                _ToolButton(
                  icon: Icons.straighten_rounded,
                  label: 'Ruler',
                  isSelected: ctrl.currentTool == CanvasTool.ruler,
                  onTap: () => ctrl.setTool(CanvasTool.ruler),
                ),
                const Spacer(),
                // Undo
                IconButton(
                  icon: const Icon(Icons.undo_rounded, size: 20),
                  onPressed: ctrl.canUndo ? ctrl.undo : null,
                  tooltip: 'Undo',
                  visualDensity: VisualDensity.compact,
                ),
                // Redo
                IconButton(
                  icon: const Icon(Icons.redo_rounded, size: 20),
                  onPressed: ctrl.canRedo ? ctrl.redo : null,
                  tooltip: 'Redo',
                  visualDensity: VisualDensity.compact,
                ),
                // Clear
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, size: 20, color: AppTheme.errorRed),
                  onPressed: ctrl.hasInk ? ctrl.clear : null,
                  tooltip: 'Clear Canvas',
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
          ),

          // Interactive Drawing Area with Custom Pointer Events
          Expanded(
            child: Listener(
              behavior: HitTestBehavior.opaque,
              onPointerDown: (e) {
                final pt = CanvasPoint(
                  x: e.localPosition.dx,
                  y: e.localPosition.dy,
                  pressure: e.kind == ui.PointerDeviceKind.stylus ? e.pressure : null,
                );
                final pointerType = e.kind == ui.PointerDeviceKind.stylus
                    ? 'pen'
                    : (e.kind == ui.PointerDeviceKind.touch ? 'touch' : 'mouse');
                ctrl.startStroke(pt, pointerType: pointerType);
              },
              onPointerMove: (e) {
                final pt = CanvasPoint(
                  x: e.localPosition.dx,
                  y: e.localPosition.dy,
                  pressure: e.kind == ui.PointerDeviceKind.stylus ? e.pressure : null,
                );
                final pointerType = e.kind == ui.PointerDeviceKind.stylus
                    ? 'pen'
                    : (e.kind == ui.PointerDeviceKind.touch ? 'touch' : 'mouse');
                ctrl.appendPoint(pt, pointerType: pointerType);
              },
              onPointerUp: (_) => ctrl.endStroke(),
              onPointerCancel: (_) => ctrl.endStroke(),
              child: CustomPaint(
                painter: _CanvasPainter(
                  strokes: ctrl.strokes,
                  showGrid: widget.showGrid,
                ),
                size: Size.infinite,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ToolButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _ToolButton({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected ? AppTheme.slate300 : Colors.transparent,
          ),
          boxShadow: isSelected
              ? [const BoxShadow(color: Colors.black12, blurRadius: 2, offset: Offset(0, 1))]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: isSelected ? AppTheme.primaryIndigo : AppTheme.slate600,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                color: isSelected ? AppTheme.primaryNavy : AppTheme.slate600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CanvasPainter extends CustomPainter {
  final List<CanvasStroke> strokes;
  final bool showGrid;

  _CanvasPainter({required this.strokes, this.showGrid = true});

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Optional background grid
    if (showGrid) {
      final gridPaint = Paint()
        ..color = const Color(0xFFE2E8F0).withValues(alpha: 0.6)
        ..strokeWidth = 0.5;

      const double step = 25.0;
      for (double x = 0; x < size.width; x += step) {
        canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
      }
      for (double y = 0; y < size.height; y += step) {
        canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
      }
    }

    // 2. Render all recorded strokes
    for (final stroke in strokes) {
      if (stroke.points.isEmpty) continue;

      final isEraser = stroke.tool == 'eraser';
      final paint = Paint()
        ..color = isEraser ? Colors.white : const Color(0xFF0F172A)
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke.width;

      if (stroke.kind == 'line' && stroke.points.length >= 2) {
        // Ruler line
        canvas.drawLine(
          Offset(stroke.points[0].x, stroke.points[0].y),
          Offset(stroke.points[1].x, stroke.points[1].y),
          paint,
        );
      } else {
        // Freehand path
        if (stroke.points.length == 1) {
          canvas.drawCircle(
            Offset(stroke.points[0].x, stroke.points[0].y),
            stroke.width / 2,
            paint..style = PaintingStyle.fill,
          );
        } else {
          final path = Path();
          path.moveTo(stroke.points[0].x, stroke.points[0].y);
          for (int i = 1; i < stroke.points.length; i++) {
            path.lineTo(stroke.points[i].x, stroke.points[i].y);
          }
          canvas.drawPath(path, paint);
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CanvasPainter oldDelegate) => true;
}
