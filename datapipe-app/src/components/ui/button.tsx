import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-[#ff6d35] text-white shadow hover:bg-[#ff6d35]/90',
        destructive: 'bg-red-500 text-white shadow-sm hover:bg-red-500/90',
        outline: 'border border-[#d7dbe2] bg-transparent shadow-sm hover:bg-[#f1f3f6] text-slate-800',
        secondary: 'bg-[#f1f3f6] text-slate-800 shadow-sm hover:bg-[#e6e8ec]',
        ghost: 'hover:bg-[#f1f3f6] text-slate-600 hover:text-slate-800',
        link: 'text-[#ff6d35] underline-offset-4 hover:underline',
        success: 'bg-emerald-500 text-white shadow-sm hover:bg-emerald-500/90',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-7 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-md px-8',
        icon: 'h-9 w-9',
        'icon-sm': 'h-7 w-7',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
