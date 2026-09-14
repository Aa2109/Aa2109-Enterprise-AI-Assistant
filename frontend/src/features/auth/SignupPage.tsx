import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'

import { signup, fetchMe } from '@/lib/api/auth.api'
import { useSessionStore } from '@/stores/useSession'
import { AuthLayout } from './AuthLayout'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

const signupSchema = z
  .object({
    full_name: z.string().min(2, 'Enter your full name'),
    email: z.email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Confirm your password'),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

type SignupForm = z.infer<typeof signupSchema>

export function SignupPage() {
  const navigate = useNavigate()
  const setSession = useSessionStore((s) => s.setSession)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({ resolver: zodResolver(signupSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      const token = await signup({
        email: values.email,
        password: values.password,
        full_name: values.full_name,
      })
      const user = await fetchMe(token.access_token)
      setSession(token.access_token, user)
      toast.success(
        user.role === 'admin'
          ? 'Account created — you are the first admin'
          : `Welcome, ${user.full_name}`,
      )
      navigate('/', { replace: true })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Sign up failed'
      setServerError(message)
      toast.error(message)
    }
  })

  return (
    <AuthLayout
      title="Create your account"
      subtitle="The first account on this instance becomes an admin."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {serverError && (
          <div className="rounded-lg border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">
            {serverError}
          </div>
        )}
        <Input
          label="Full name"
          autoComplete="name"
          placeholder="Aashif Mohammed"
          error={errors.full_name?.message}
          {...register('full_name')}
        />
        <Input
          label="Work email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 8 characters"
          error={errors.password?.message}
          {...register('password')}
        />
        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          placeholder="Repeat your password"
          error={errors.confirm_password?.message}
          {...register('confirm_password')}
        />
        <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-fg-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent-strong hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}