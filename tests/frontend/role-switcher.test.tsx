import { render, screen } from "@testing-library/react";
import { RoleSwitcher } from "../../app/web/src/components/role-switcher";

test("role switcher exposes all required product roles", () => {
  render(<RoleSwitcher />);

  expect(screen.getByRole("link", { name: /customer/i })).toBeVisible();
  expect(screen.getByRole("link", { name: /restaurant/i })).toBeVisible();
  expect(screen.getByRole("link", { name: /courier/i })).toBeVisible();
  expect(screen.getByRole("link", { name: /admin/i })).toBeVisible();

  expect(screen.getByRole("link", { name: /courier/i })).toHaveAttribute(
    "href",
    "/courier",
  );
  expect(screen.getByRole("link", { name: /courier/i })).toHaveAttribute(
    "aria-current",
    "page",
  );
});
