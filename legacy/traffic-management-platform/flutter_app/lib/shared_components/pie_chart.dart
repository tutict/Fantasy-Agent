import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class TrafficViolationPieChart extends StatelessWidget {
  final Map<String, int> typeCountMap;

  const TrafficViolationPieChart({super.key, required this.typeCountMap});

  @override
  Widget build(BuildContext context) {
    if (typeCountMap.isEmpty) {
      return Center(child: Text('chart.noOffenseData'.tr));
    }

    final dataList = typeCountMap.entries.toList();
    final totalCount = typeCountMap.values.reduce((a, b) => a + b);
    final colors = List<Color>.generate(
      dataList.length,
      (index) => Colors.primaries[index % Colors.primaries.length][500]!,
    );

    return SizedBox(
      height: 300,
      child: Stack(
        children: [
          PieChart(
            PieChartData(
              sections: _buildPieChartSections(dataList, colors, totalCount),
              sectionsSpace: 2,
              centerSpaceRadius: 40,
              borderData: FlBorderData(show: false),
            ),
          ),
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'chart.total'.tr,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.black,
                  ),
                ),
                Text(
                  totalCount.toString(),
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.black,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<PieChartSectionData> _buildPieChartSections(
    List<MapEntry<String, int>> dataList,
    List<Color> colors,
    int totalCount,
  ) {
    return List.generate(dataList.length, (index) {
      final entry = dataList[index];
      final value = entry.value.toDouble();
      final percentage = (value / totalCount * 100).toStringAsFixed(1);

      return PieChartSectionData(
        value: value,
        color: colors[index],
        radius: 100,
        title: '$percentage%',
        titleStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Colors.white,
        ),
        badgeWidget: _buildBadgeWidget(entry.key, colors[index]),
        badgePositionPercentageOffset: 1.2,
      );
    });
  }

  Widget _buildBadgeWidget(String type, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(12),
        boxShadow: const [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 4,
            offset: Offset(2, 2),
          ),
        ],
      ),
      child: Text(
        type,
        style: const TextStyle(
          fontSize: 12,
          color: Colors.white,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
