import { Outlet } from "react-router"

export function AuthLayout() {
  return (
    <div className="flex w-full h-full min-h-screen items-center justify-center">
      <Outlet />
    </div>
  )
}
