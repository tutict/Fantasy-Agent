import 'package:final_assignment_front/features/dashboard/views/admin/pages/admin_personal_page.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';

class ManagerPersonalPage extends AdminPersonalPage {
  const ManagerPersonalPage({super.key})
      : super(
          titleKey: 'personal.title',
          pageType: DashboardPageType.manager,
          logoutTooltipKey: 'common.logout',
          logoutConfirmTitleKey: 'settings.confirmLogoutTitle',
          logoutConfirmBodyKey: 'settings.confirmLogoutMessage',
          noDataKey: 'common.notFilled',
        );
}
