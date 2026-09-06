subroutine superhound_external(nutc,dd8)

  use, intrinsic :: iso_c_binding, only: c_int,c_float
  implicit none

  integer, intent(in) :: nutc
  real, intent(in) :: dd8(180000)
  integer(c_int) :: rc
  integer, save :: last_nutc=-1

  interface
     integer(c_int) function jtdx_superhound_external_c(nutc_c,samples,npts) &
          bind(C,name='jtdx_superhound_external_c')
       use, intrinsic :: iso_c_binding, only: c_int,c_float
       integer(c_int), value :: nutc_c
       real(c_float), intent(in) :: samples(*)
       integer(c_int), value :: npts
     end function jtdx_superhound_external_c
  end interface

  if(nutc.eq.last_nutc) return
  last_nutc=nutc

  rc=jtdx_superhound_external_c(int(nutc,c_int),real(dd8,c_float),180000_c_int)

  ! P1 is deliberately non-fatal. If the external helper is absent or fails,
  ! native JTDX FT8/Hound decoding continues unchanged.
  if(rc.eq.-999999_c_int) write(*,*) rc

  return
end subroutine superhound_external
