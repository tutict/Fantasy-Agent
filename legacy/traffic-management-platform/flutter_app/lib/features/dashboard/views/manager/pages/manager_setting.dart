import 'package:final_assignment_front/features/dashboard/views/admin/pages/admin_setting_page.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';

class ManagerSetting extends AdminSettingPage {
  const ManagerSetting({super.key})
      : super(
          titleKey: 'settings.title',
          pageType: DashboardPageType.manager,
        );
}
