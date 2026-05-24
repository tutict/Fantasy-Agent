import 'package:final_assignment_front/config/themes/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ChangeThemes extends StatefulWidget {
  const ChangeThemes({super.key});

  @override
  State<ChangeThemes> createState() => _ChangeThemes();
}

class _ChangeThemes extends State<ChangeThemes> {
  String selectedTheme = 'basicLight';

  final Map<String, ThemeData> themes = {
    'basicLight': AppTheme.basicLight,
    'basicDark': AppTheme.basicDark,
    'ionicLight': AppTheme.ionicLightTheme,
    'ionicDark': AppTheme.ionicDarkTheme,
    'materialLight': AppTheme.materialLightTheme,
    'materialDark': AppTheme.materialDarkTheme,
  };

  void _toggleTheme(String themeKey) {
    setState(() {
      selectedTheme = themeKey;
      Get.changeTheme(themes[themeKey]!);
    });
  }

  String _themeLabel(String themeKey) {
    return 'settings.theme.$themeKey'.tr;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('common.toggleTheme'.tr),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'settings.themeDialogTitle'.tr,
              style: const TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 20),
            RadioGroup<String>(
              groupValue: selectedTheme,
              onChanged: (value) {
                if (value != null) {
                  _toggleTheme(value);
                }
              },
              child: Column(
                children: [
                  for (final themeKey in themes.keys)
                    RadioListTile<String>(
                      title: Text(_themeLabel(themeKey)),
                      value: themeKey,
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
