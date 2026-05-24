import 'package:final_assignment_front/features/dashboard/views/admin/pages/admin_business_processing.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';

class ManagerBusinessProcessing extends AdminBusinessProcessing {
  const ManagerBusinessProcessing({super.key})
      : super(
          titleKey: 'manager.business.title',
          enterLabelKey: 'manager.business.enter',
          pageType: DashboardPageType.manager,
        );
}
