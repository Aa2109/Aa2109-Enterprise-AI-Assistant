import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'

import { login, fetchMe } from '@/lib/api/auth.api'
import { useSessionStore } from '@/stores/useSession'
import { AuthLayout } from './AuthLayout'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

const loginSchema = z.object({
  email: z.email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setSession = useSessionStore((s) => s.setSession)
  const [serverError, setServerError] = useState<string | null>(null)

  // Set by the API client (via router state) or the redirect URL when an
  // auth token expired mid-session — show a clear notice instead of a
  // blank login page.
  const reason = (location.state as { reason?: string } | null)?.reason
    ?? new URLSearchParams(location.search).get('reason')
  const sessionExpired = reason === 'session_expired'

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      const token = await login(values)
      const user = await fetchMe(token.access_token)
      setSession(token.access_token, user)
      toast.success(`Welcome back, ${user.full_name}`)
      navigate('/', { replace: true })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed'
      setServerError(message)
      toast.error(message)
    }
  })

  return (
    <AuthLayout title="Sign in" subtitle="Continue to your assistant workspace.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {serverError && (
          <div className="rounded-lg border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">
            {serverError}
          </div>
        )}
        {!serverError && sessionExpired && (
          <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            <span>
              Your session has expired. Please sign in again to continue.
            </span>
          </div>
        )}
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          error={errors.password?.message}
          {...register('password')}
        />
        <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-muted">
        New to this instance?{' '}
        <Link to="/signup" className="font-medium text-accent-strong hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  )
}