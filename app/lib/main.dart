import 'package:flutter/material.dart';
import 'package:rive/rive.dart' as rive;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await rive.RiveNative.init();
  runApp(const JptakuApp());
}

class JptakuApp extends StatelessWidget {
  const JptakuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JPTAKU Rive PoC',
      theme: ThemeData.dark(useMaterial3: true),
      home: const RiveTestPage(),
    );
  }
}

class RiveTestPage extends StatefulWidget {
  const RiveTestPage({super.key});

  @override
  State<RiveTestPage> createState() => _RiveTestPageState();
}

class _RiveTestPageState extends State<RiveTestPage> {
  rive.File? _file;
  rive.RiveWidgetController? _controller;
  final Map<String, rive.NumberInput> _numberInputs = {};
  final Map<String, double> _sliderValues = {};
  String _debugInfo = 'Loading...';
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadRive();
  }

  Future<void> _loadRive() async {
    try {
      final file = await rive.File.asset(
        'assets/facial_expression.riv',
        riveFactory: rive.Factory.flutter,
      );
      if (file == null) {
        setState(() {
          _debugInfo = 'Error: Failed to load .riv file';
          _loading = false;
        });
        return;
      }

      final controller = rive.RiveWidgetController(file);
      final sm = controller.stateMachine;

      final info = StringBuffer();
      info.writeln('Artboard: ${controller.artboard.name}');
      info.writeln('State Machine: ${sm.name}');

      // Discover inputs via deprecated but functional API
      // ignore: deprecated_member_use
      final inputs = sm.inputs;
      info.writeln('Inputs (${inputs.length}):');

      for (final input in inputs) {
        final type = input is rive.NumberInput
            ? 'Number'
            : input is rive.TriggerInput
                ? 'Trigger'
                : 'Unknown';
        info.writeln('  [$type] ${input.name}');

        if (input is rive.NumberInput) {
          _numberInputs[input.name] = input;
          _sliderValues[input.name] = input.value;
        }
      }

      // Also try getting number inputs by common names
      for (final name in [
        'Happy',
        'Sad',
        'Angry',
        'Surprised',
        'Disgust',
        'Fear',
      ]) {
        final n = sm.number(name);
        if (n != null && !_numberInputs.containsKey(name)) {
          _numberInputs[name] = n;
          _sliderValues[name] = n.value;
          info.writeln('  [Number] $name (found by name)');
        }
      }

      setState(() {
        _file = file;
        _controller = controller;
        _debugInfo = info.toString();
        _loading = false;
      });
    } catch (e, st) {
      setState(() {
        _debugInfo = 'Error: $e\n$st';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('JPTAKU Rive PoC')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Rive character
                Expanded(
                  flex: 2,
                  child: _controller != null
                      ? rive.RiveWidget(controller: _controller!)
                      : Center(child: Text(_debugInfo)),
                ),
                const Divider(height: 1),
                // Controls
                Expanded(
                  flex: 3,
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(8),
                          color: Colors.black54,
                          child: SelectableText(
                            _debugInfo,
                            style: const TextStyle(
                                fontFamily: 'monospace', fontSize: 11),
                          ),
                        ),
                        const SizedBox(height: 16),
                        if (_numberInputs.isNotEmpty)
                          const Text('Expression Controls',
                              style: TextStyle(
                                  fontSize: 16, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        ..._numberInputs.entries.map(_buildSlider),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildSlider(MapEntry<String, rive.NumberInput> entry) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 120,
            child: Text(entry.key, style: const TextStyle(fontSize: 12)),
          ),
          Expanded(
            child: Slider(
              value: (_sliderValues[entry.key] ?? 0).clamp(0.0, 100.0),
              min: 0,
              max: 100,
              onChanged: (v) {
                entry.value.value = v;
                setState(() => _sliderValues[entry.key] = v);
              },
            ),
          ),
          SizedBox(
            width: 40,
            child: Text(
              (_sliderValues[entry.key] ?? 0).toStringAsFixed(0),
              style: const TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller?.dispose();
    _file?.dispose();
    super.dispose();
  }
}
